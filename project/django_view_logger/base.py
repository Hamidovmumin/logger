"""
django_view_logger.base
========================

BaseLogger — modulun əsas loglama mühərrikidir.

MÜHÜM: Bu fayl daxilində Python-un standart ``logging`` modulu
İSTİFADƏ EDİLMİR. Bütün terminal çıxışı ``print()`` / ``sys.stdout`` /
``sys.stderr`` vasitəsilə, fayla yazma isə standart fayl I/O ilə həyata
keçirilir.

Sinif heç bir konkret Django layihəsinə, modelə və ya app-ə bağlı deyil.
Django-ya olan yeganə asılılıq ``django.db.connection``-dır və o da
yalnız funksiya daxilində, lazy şəkildə import olunur — Django quraşdırılıb
konfiqurasiya olunmadan modul import edilə bilsin deyə.
"""

import os
import sys
import json
import re
import copy
import hashlib
import threading
import traceback
from datetime import datetime


class BaseLogger:
    """
    Terminala (rəngli), fayla (``logs/YYYY-MM-DD.log``) və (mümkünsə)
    Django bazasına (``view_logs`` cədvəli) paralel yazan, hash-zəncirli,
    həssas-məlumat maskalayan əsas logger sinfi.
    """

    # ------------------------------------------------------------------
    # Səviyyələr
    # ------------------------------------------------------------------
    LEVELS = {
        "DEBUG": 10,
        "INFO": 20,
        "SUCCESS": 25,
        "WARNING": 30,
        "ERROR": 40,
        "CRITICAL": 50,
        "SECURITY_ALERT": 60,       # Anomaliya / enumerasiya aşkarlanması
        "CANARY_TRIGGERED": 70,     # Honeypot tələsinə toxunulub
    }

    # stdout-a yazılacaq səviyyələr, qalanları stderr-ə gedir
    STDOUT_LEVELS = {"DEBUG", "INFO", "SUCCESS"}

    COLORS = {
        "DEBUG": "\033[36m",              # cyan
        "INFO": "\033[34m",               # göy
        "SUCCESS": "\033[32m",            # yaşıl
        "WARNING": "\033[33m",            # sarı
        "ERROR": "\033[31m",              # qırmızı
        "CRITICAL": "\033[1;31m",         # bold qırmızı
        "SECURITY_ALERT": "\033[1;35m",   # bold magenta
        "CANARY_TRIGGERED": "\033[1;97;41m",  # ağ yazı, qırmızı fon
    }
    RESET = "\033[0m"

    # Minimum log səviyyəsi (bundan aşağı olanlar göstərilmir)
    MIN_LEVEL = int(os.environ.get("DJANGO_VIEW_LOGGER_MIN_LEVEL", "10"))

    # ------------------------------------------------------------------
    # Həssas məlumatların maskalanması üçün açar adları
    # ------------------------------------------------------------------
    SENSITIVE_KEYS = {
        "password", "password1", "password2", "token", "access_token",
        "refresh_token", "authorization", "cookie", "sessionid",
        "csrfmiddlewaretoken", "otp", "pin", "secret", "api_key",
    }

    # Sətir dəyərləri daxilində axtarılan həssas nümunələr (JWT, kart nömrəsi)
    _JWT_PATTERN = re.compile(r"eyJ[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+")
    _CARD_PATTERN = re.compile(r"\b(?:\d[ -]?){13,19}\b")

    # ------------------------------------------------------------------
    # WAF-lite hücum imzaları
    # ------------------------------------------------------------------
    _ATTACK_SIGNATURES = {
        "SQL_INJECTION": re.compile(
            r"(\bor\b\s+\d+\s*=\s*\d+|\bunion\b\s+\bselect\b|--\s|;--|/\*.*?\*/|\bdrop\b\s+\btable\b|\bselect\b.+\bfrom\b)",
            re.IGNORECASE,
        ),
        "XSS": re.compile(
            r"(<script[^>]*>|javascript:|onerror\s*=|onload\s*=|<img[^>]+onerror)",
            re.IGNORECASE,
        ),
        "PATH_TRAVERSAL": re.compile(
            r"(\.\./|\.\.\\|%2e%2e%2f|%2e%2e/|\.\.%2f)",
            re.IGNORECASE,
        ),
    }

    # ------------------------------------------------------------------
    # Hash-zəncir və DB üçün class-səviyyəli paylaşılan state
    # ------------------------------------------------------------------
    _last_hash = None
    _hash_lock = threading.Lock()
    _db_lock = threading.Lock()
    _db_table_ready = False
    _file_lock = threading.Lock()

    GENESIS_HASH = "0" * 64
    DB_TABLE_NAME = "view_logs"

    # ------------------------------------------------------------------
    # Konstruktor / bind
    # ------------------------------------------------------------------
    def __init__(self, name, context=None):
        self.name = name
        self.context = dict(context) if context else {}

    def bind(self, **kwargs):
        """
        Verilmiş açar/dəyərləri daimi kontekstə əlavə edərək YENİ bir
        logger nüsxəsi qaytarır (mövcud logger dəyişdirilmir).

            request_logger = logger.bind(owner_id=25)
            request_logger.info("Sahibkar yeniləndi")
        """
        new_logger = copy.copy(self)
        new_logger.context = {**self.context, **kwargs}
        return new_logger

    # ------------------------------------------------------------------
    # Public log metodları
    # ------------------------------------------------------------------
    def debug(self, message, **kwargs):
        self._log("DEBUG", message, **kwargs)

    def info(self, message, **kwargs):
        self._log("INFO", message, **kwargs)

    def success(self, message, **kwargs):
        self._log("SUCCESS", message, **kwargs)

    def warning(self, message, **kwargs):
        self._log("WARNING", message, **kwargs)

    def error(self, message, **kwargs):
        self._log("ERROR", message, **kwargs)

    def critical(self, message, **kwargs):
        self._log("CRITICAL", message, **kwargs)

    def exception(self, message, exception=None, **kwargs):
        """
        Xətanı traceback ilə birlikdə ERROR səviyyəsində loglayır.
        ``exception`` parametri veriləndə onun öz traceback-i istifadə
        olunur, verilməyəndə cari ``sys.exc_info()`` istifadə edilir.
        """
        if exception is not None:
            tb_text = "".join(
                traceback.format_exception(type(exception), exception, exception.__traceback__)
            )
            exc_repr = f"{type(exception).__name__}: {exception}"
        else:
            tb_text = traceback.format_exc()
            exc_repr = None

        self._log("ERROR", message, exception=exc_repr, traceback=tb_text, **kwargs)

    # ------------------------------------------------------------------
    # Daxili: əsas log axını
    # ------------------------------------------------------------------
    def _log(self, level, message, **kwargs):
        level = level.upper()
        level_value = self.LEVELS.get(level, 0)

        if level_value < self.MIN_LEVEL:
            return

        merged_context = {**self.context, **kwargs}
        masked_context = self._mask_sensitive(merged_context)

        # WAF-lite: hücum imzası axtarışı
        detected_signatures = self._detect_attack_signatures(merged_context)
        if detected_signatures:
            message = f"[POTENTIAL ATTACK SIGNATURE DETECTED: {', '.join(sorted(detected_signatures))}] {message}"
            # Hücum imzası aşkarlansa, səviyyəni minimum SECURITY_ALERT-ə qaldırırıq
            if level_value < self.LEVELS["SECURITY_ALERT"]:
                level = "SECURITY_ALERT"
                level_value = self.LEVELS["SECURITY_ALERT"]

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        extra_str = " | ".join(f"{k}={self._stringify(v)}" for k, v in masked_context.items())
        line = f"[{timestamp}] [{level}] [{self.name}] {message}"
        if extra_str:
            line = f"{line} | {extra_str}"

        # 1) Terminal
        self._write_to_terminal(level, line)

        # 2) Hash-zəncir hesablanması
        prev_hash = self._get_last_hash()
        entry_hash = hashlib.sha256((prev_hash + line).encode("utf-8")).hexdigest()
        self._set_last_hash(entry_hash)

        # 3) Fayla yazma (logs/YYYY-MM-DD.log)
        self._write_to_file(line, entry_hash)

        # 4) Bazaya yazma (mövcuddursa)
        self._write_to_db(
            timestamp=timestamp,
            level=level,
            message=message,
            context=masked_context,
            entry_hash=entry_hash,
            prev_hash=prev_hash,
        )

    @staticmethod
    def _stringify(value):
        if isinstance(value, (dict, list, tuple)):
            try:
                return json.dumps(value, default=str, ensure_ascii=False)
            except Exception:
                return str(value)
        return value

    # ------------------------------------------------------------------
    # Terminal çıxışı
    # ------------------------------------------------------------------
    def _write_to_terminal(self, level, line):
        color = self.COLORS.get(level, "")
        colored_line = f"{color}{line}{self.RESET}"
        if level in self.STDOUT_LEVELS:
            sys.stdout.write(colored_line + "\n")
            sys.stdout.flush()
        else:
            sys.stderr.write(colored_line + "\n")
            sys.stderr.flush()

    # ------------------------------------------------------------------
    # Fayla yazma (gündəlik rotasiya)
    # ------------------------------------------------------------------
    def _write_to_file(self, line, entry_hash):
        try:
            log_dir = os.path.join(os.getcwd(), "logs")
            with self._file_lock:
                os.makedirs(log_dir, exist_ok=True)
                filename = datetime.now().strftime("%Y-%m-%d") + ".log"
                filepath = os.path.join(log_dir, filename)
                with open(filepath, "a", encoding="utf-8") as f:
                    f.write(f"{line} | hash={entry_hash}\n")
        except Exception:
            # Fayl sistemi əlçatan olmasa belə logger dayanmamalıdır
            pass

    # ------------------------------------------------------------------
    # Hash-zəncir idarəetməsi
    # ------------------------------------------------------------------
    def _get_last_hash(self):
        with self._hash_lock:
            if BaseLogger._last_hash is None:
                BaseLogger._last_hash = self._load_last_hash_from_db() or self.GENESIS_HASH
            return BaseLogger._last_hash

    def _set_last_hash(self, new_hash):
        with self._hash_lock:
            BaseLogger._last_hash = new_hash

    def _load_last_hash_from_db(self):
        try:
            from django.db import connection
            self._ensure_db_table(connection)
            with connection.cursor() as cursor:
                cursor.execute(
                    f"SELECT log_hash FROM {self.DB_TABLE_NAME} ORDER BY id DESC LIMIT 1"
                )
                row = cursor.fetchone()
                return row[0] if row else None
        except Exception:
            return None

    # ------------------------------------------------------------------
    # Baza inteqrasiyası (raw SQL, migrasiya tələb etmir)
    # ------------------------------------------------------------------
    def _ensure_db_table(self, connection):
        with BaseLogger._db_lock:
            if BaseLogger._db_table_ready:
                return
            try:
                existing_tables = connection.introspection.table_names()
                if self.DB_TABLE_NAME not in existing_tables:
                    vendor = getattr(connection, "vendor", "")
                    if vendor == "postgresql":
                        id_column = "id SERIAL PRIMARY KEY"
                    elif vendor == "sqlite":
                        id_column = "id INTEGER PRIMARY KEY AUTOINCREMENT"
                    elif vendor == "mysql":
                        id_column = "id INTEGER PRIMARY KEY AUTO_INCREMENT"
                    else:
                        id_column = "id INTEGER PRIMARY KEY"

                    with connection.cursor() as cursor:
                        cursor.execute(
                            f"""
                            CREATE TABLE {self.DB_TABLE_NAME} (
                                {id_column},
                                created_at VARCHAR(32),
                                level VARCHAR(32),
                                logger_name VARCHAR(255),
                                message TEXT,
                                context TEXT,
                                log_hash VARCHAR(64),
                                prev_hash VARCHAR(64)
                            )
                            """
                        )
                BaseLogger._db_table_ready = True
            except Exception:
                # Baza hazır deyilsə (məsələn, migrasiyadan əvvəl) sakitcə keç
                pass

    def _write_to_db(self, timestamp, level, message, context, entry_hash, prev_hash):
        try:
            from django.db import connection
            self._ensure_db_table(connection)
            with connection.cursor() as cursor:
                cursor.execute(
                    f"""
                    INSERT INTO {self.DB_TABLE_NAME}
                        (created_at, level, logger_name, message, context, log_hash, prev_hash)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """,
                    [
                        timestamp,
                        level,
                        self.name,
                        message,
                        json.dumps(context, default=str, ensure_ascii=False),
                        entry_hash,
                        prev_hash,
                    ],
                )
        except Exception:
            # Django/DB mövcud olmasa belə logger işləməyə davam etməlidir
            pass

    # ------------------------------------------------------------------
    # DLP: Həssas məlumatların dərin maskalanması
    # ------------------------------------------------------------------
    @classmethod
    def _mask_sensitive(cls, value):
        if isinstance(value, dict):
            masked = {}
            for k, v in value.items():
                if str(k).lower() in cls.SENSITIVE_KEYS:
                    masked[k] = "***"
                else:
                    masked[k] = cls._mask_sensitive(v)
            return masked
        if isinstance(value, (list, tuple)):
            return [cls._mask_sensitive(v) for v in value]
        if isinstance(value, str):
            return cls._mask_string_patterns(value)
        return value

    @classmethod
    def _mask_string_patterns(cls, text):
        text = cls._JWT_PATTERN.sub("***", text)
        text = cls._CARD_PATTERN.sub("***", text)
        return text

    # ------------------------------------------------------------------
    # WAF-lite: sətir dəyərləri daxilində hücum imzası axtarışı
    # ------------------------------------------------------------------
    @classmethod
    def _detect_attack_signatures(cls, value, found=None):
        if found is None:
            found = set()
        if isinstance(value, dict):
            for v in value.values():
                cls._detect_attack_signatures(v, found)
        elif isinstance(value, (list, tuple)):
            for v in value:
                cls._detect_attack_signatures(v, found)
        elif isinstance(value, str):
            for label, pattern in cls._ATTACK_SIGNATURES.items():
                if pattern.search(value):
                    found.add(label)
        return found
