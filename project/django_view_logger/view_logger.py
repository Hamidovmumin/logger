"""
django_view_logger.view_logger
================================

ViewLogger — Django view-ləri daxilində istifadə üçün nəzərdə tutulmuş,
``BaseLogger``-dən miras alan xüsusi logger.

Heç bir konkret User modelinə, app-ə və ya URL konfiqurasiyasına bağlı
deyil — bütün məlumatları ötürülən ``request`` obyektindən generic
şəkildə (``getattr``) çıxarır.
"""

import time
import uuid
import threading
import contextvars
from collections import defaultdict, deque

from .base import BaseLogger


# Thread-safe / async-safe request_id izlənməsi üçün contextvar.
# Hər request üçün ayrıca "kontekst" saxlayır, thread-lər arasında qarışmır.
_request_id_ctx_var = contextvars.ContextVar("django_view_logger_request_id", default=None)


def get_current_request_id():
    """Cari kontekstdə (əgər varsa) aktiv request_id-ni qaytarır."""
    return _request_id_ctx_var.get()


class ViewLogger(BaseLogger):
    """
    Django view-lərində istifadə edilən, request-context-aware logger.

        logger = ViewLogger.from_request(request, view_name="owner_list")
        logger.request_started()
        ...
        logger.request_finished(status_code=200)
    """

    # ------------------------------------------------------------------
    # Anomaliya / enumerasiya (brute-force scanning) aşkarlanması
    # ------------------------------------------------------------------
    ANOMALY_WINDOW_SECONDS = 60      # neçə saniyəlik pəncərədə sayılsın
    ANOMALY_THRESHOLD = 5            # bu ədədə çatanda SECURITY_ALERT

    # IP -> deque(timestamps) — class-səviyyəli, bütün nüsxələr arasında paylaşılır
    _ip_activity = defaultdict(deque)
    _activity_lock = threading.Lock()

    def __init__(self, name, context=None, canary_fields=None):
        super().__init__(name, context)
        self.canary_fields = list(canary_fields) if canary_fields else []
        self._start_time = None

    # ------------------------------------------------------------------
    # Request-dən logger yaratmaq
    # ------------------------------------------------------------------
    @classmethod
    def from_request(cls, request, view_name, canary_fields=None):
        """
        Django request obyektindən avtomatik context çıxararaq
        ViewLogger nüsxəsi yaradır.

        ``canary_fields`` — honeypot/tələ sahə adları. Bot/skript bu
        sahələrə məlumat yazarsa, ``CANARY_TRIGGERED`` səviyyəsində
        alarm işə düşür.
        """
        request_id = uuid.uuid4().hex[:8]
        _request_id_ctx_var.set(request_id)

        user = getattr(request, "user", None)
        user_id = None
        username = None
        if user is not None:
            # Custom User modelləri ilə də işləmək üçün generic yanaşma
            user_id = getattr(user, "id", None) or getattr(user, "pk", None)
            if hasattr(user, "get_username"):
                try:
                    username = user.get_username()
                except Exception:
                    username = getattr(user, "username", None)
            else:
                username = getattr(user, "username", None)
            # Django-nun AnonymousUser-i is_authenticated=False saxlayır
            if getattr(user, "is_authenticated", True) is False:
                user_id = None

        ip_address = cls._extract_client_ip(request)
        query_params = cls._extract_query_params(request)

        context = {
            "view_name": view_name,
            "method": getattr(request, "method", None),
            "path": getattr(request, "path", None),
            "user_id": user_id,
            "username": username,
            "ip_address": ip_address,
            "query_params": query_params,
            "request_id": request_id,
        }

        logger = cls(f"view.{view_name}", context=context, canary_fields=canary_fields)
        logger._check_canary(request)
        return logger

    # ------------------------------------------------------------------
    # Request-dən köməkçi çıxarış funksiyaları
    # ------------------------------------------------------------------
    @staticmethod
    def _extract_client_ip(request):
        meta = getattr(request, "META", None) or {}
        forwarded_for = meta.get("HTTP_X_FORWARDED_FOR")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        return meta.get("REMOTE_ADDR", "unknown")

    @staticmethod
    def _extract_query_params(request):
        get_params = getattr(request, "GET", None)
        if get_params is None:
            return {}
        try:
            return {k: v for k, v in get_params.items()}
        except Exception:
            return {}

    # ------------------------------------------------------------------
    # Honeypot / Canary tələ sahə aşkarlanması
    # ------------------------------------------------------------------
    def _check_canary(self, request):
        if not self.canary_fields:
            return

        triggered_fields = []
        for source_name in ("POST", "GET"):
            source = getattr(request, source_name, None)
            if not source:
                continue
            for field in self.canary_fields:
                try:
                    value = source.get(field)
                except Exception:
                    value = None
                if value:
                    triggered_fields.append(field)

        if triggered_fields:
            ip_address = self.context.get("ip_address")
            self._log(
                "CANARY_TRIGGERED",
                "Honeypot/canary sahəyə toxunuldu — avtomatlaşdırılmış bot/hücumçu ehtimalı",
                canary_fields=triggered_fields,
            )
            self._trigger_ip_block(ip_address, reason="canary_field_triggered")

    def _trigger_ip_block(self, ip_address, reason):
        """
        IP bloklama üçün trigger nöqtəsi.

        Bu modul heç bir konkret firewall/WAF-a bağlı olmadığından real
        bloklama əməliyyatı burada icra edilmir — layihə səviyyəsində bu
        metod override edilərək (subclass və ya monkey-patch ilə) real
        firewall/IPTables/Cloudflare/WAF API-sinə qoşula bilər.
        """
        self._log(
            "SECURITY_ALERT",
            f"IP bloklama trigger-i işə salındı: {ip_address}",
            reason=reason,
            ip_address=ip_address,
        )

    # ------------------------------------------------------------------
    # Anomaliya / enumerasiya izlənməsi
    # ------------------------------------------------------------------
    @classmethod
    def _register_suspicious_event(cls, ip_address):
        if not ip_address:
            return False
        now = time.time()
        with cls._activity_lock:
            events = cls._ip_activity[ip_address]
            events.append(now)
            while events and now - events[0] > cls.ANOMALY_WINDOW_SECONDS:
                events.popleft()
            return len(events) >= cls.ANOMALY_THRESHOLD

    # ------------------------------------------------------------------
    # Request lifecycle metodları
    # ------------------------------------------------------------------
    def request_started(self):
        self._start_time = time.time()
        self.info("Request başladı")

    def request_finished(self, status_code):
        duration_ms = None
        if self._start_time is not None:
            duration_ms = round((time.time() - self._start_time) * 1000, 2)
        self.success(
            "Request tamamlandı",
            status_code=status_code,
            duration_ms=duration_ms,
        )

    # ------------------------------------------------------------------
    # Ümumi mesaj metodları
    # ------------------------------------------------------------------
    def message(self, text, **kwargs):
        self.info(text, **kwargs)

    def validation_error(self, text, **kwargs):
        self.warning(text, error_type="validation_error", **kwargs)

    def not_found(self, text, **kwargs):
        ip_address = self.context.get("ip_address")
        is_anomalous = self._register_suspicious_event(ip_address)
        self.warning(text, error_type="not_found", **kwargs)
        if is_anomalous:
            self._log(
                "SECURITY_ALERT",
                f"Anomaliya aşkarlandı: {ip_address} ünvanından qısa müddətdə təkrarlanan 404 sorğular",
                ip_address=ip_address,
                pattern="repeated_not_found",
            )

    def permission_denied(self, text, **kwargs):
        ip_address = self.context.get("ip_address")
        is_anomalous = self._register_suspicious_event(ip_address)
        self.warning(text, error_type="permission_denied", **kwargs)
        if is_anomalous:
            self._log(
                "SECURITY_ALERT",
                f"Anomaliya aşkarlandı: {ip_address} ünvanından qısa müddətdə təkrarlanan icazə xətaları",
                ip_address=ip_address,
                pattern="repeated_permission_denied",
            )

    def request_error(self, text, exception=None, **kwargs):
        self.exception(text, exception=exception, **kwargs)
