from .base import BaseLogger
import uuid

class ViewLogger(BaseLogger):
    @classmethod
    def from_request(cls, request,view_name:str,min_level="DEBUG", db_log=False):
        user = getattr(request, 'user', None)
        user_id,username = cls._extract_user_info(user)

        context = {
            "view_name": view_name,
            "method": getattr(request, 'method', None),
            "path": getattr(request, 'path', None),
            "user_id": user_id,
            "username": username,
            "ip_address": cls._get_client_ip(request),
            "request_id": cls._get_request_id(request),
        }
        query_params = cls._get_query_params(request)
        if query_params:
            context["query_params"] = query_params

        logger_name = f"view.{view_name}"
        return cls(name=logger_name, context=context, min_level=min_level ,db_log=db_log)


    @staticmethod
    def _extract_user_info(user):
        if not user:
            return None,None

        is_authenticated = getattr(user, 'is_authenticated', False)
        if not is_authenticated:
            return None,None

        user_id = getattr(user, 'pk', None)
        get_username = getattr(user, "get_username", None)
        username = get_username() if callable(get_username) else None
        if not username:
            username = getattr(user, "username", None)

        return user_id, username

    @staticmethod
    def _get_client_ip(request):
        forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR", None)
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()

        real_ip = request.META.get("REMOTE_ADDR", None)
        if real_ip:
            return real_ip.strip()

        return request.META.get("REMOTE_ADDR")

    @staticmethod
    def _get_request_id(request):
        meta = getattr(request, 'META', None)
        request_id = meta.get("HTTP_X_REQUEST_ID") or getattr(request, "request_id", None)
        if not request_id:
            request_id = uuid.uuid4().hex[:8]
        return request_id

    @staticmethod
    def _get_query_params(request):
        get_params = getattr(request, "GET", None)
        if get_params is None:
            return {}
        try:
            return get_params.dict()
        except AttributeError:
            try:
                return dict(get_params)
            except Exception:
                return {}


    def request_started(self,**extra):
        self.info("Request başladı", **extra)

    def request_finished(self,status_code=200,**extra):
        self.success('Request tamamlandı',status_code=status_code,**extra)

    def message(self,text,**extra):
        self.info(text,**extra)

    def validation_error(self, text, **extra):
        self.warning(text, **extra)

    def not_found(self, text, **extra):
        self.warning(text, **extra)

    def permission_denied(self, text, **extra):
        self.warning(text, **extra)

    def request_error(self, text, exception=None, **extra):
        self.exception(text, exc=exception, **extra)