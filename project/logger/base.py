import os
from datetime import datetime
import sys
import traceback

LEVELS = {
    "DEBUG": 10,
    "INFO": 20,
    "SUCCESS": 25,
    "WARNING": 30,
    "ERROR": 40,
    "CRITICAL": 50,
}


STDOUT_LEVELS = {"DEBUG", "INFO", "SUCCESS"}
STDERR_LEVELS = {"WARNING", "ERROR", "CRITICAL"}


SENSITIVE_KEYS = {
    "password",
    "password1",
    "password2",
    "token",
    "access_token",
    "refresh_token",
    "authorization",
    "cookie",
    "sessionid",
    "csrfmiddlewaretoken",
    "otp",
    "pin",
    "secret",
    "api_key",
}

MASK = "***"

DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


class BaseLogger:

    def __init__(self,name="logger",context = None,min_level = "DEBUG",db_log=False,log_file=None):
        self.name = name
        self.context = context if context else {}
        self.min_level = min_level
        self.db_log =db_log
        self.log_file = log_file

    def _mask_dict(self,data:dict)->dict:
        masked = {}
        for key,value in data.items():
            is_sensitive = isinstance(value, str) and key.lower() in SENSITIVE_KEYS
            if is_sensitive:
                masked[key] = MASK
            elif isinstance(value,dict):
                masked[key] = self._mask_dict(value)
            else:
                masked[key] = value
        return masked


    def _is_enabled(self,level):
        return LEVELS.get(level,0) >= LEVELS.get(self.min_level,0)

    def _format_extra(self,data)->str:
        return ' | '.join(f'{key}={value}' for key,value in data.items())

    def _format_message(self,level,message,extra):
        timestamp  = datetime.now().strftime(DATE_FORMAT)
        base = f'[{timestamp}] [{level}] [{self.name}] {message}'

        merged = {**self.context,**extra}
        masked = self._mask_dict(data=merged)

        if masked:
            base = f'{base}: {self._format_extra(data=masked)}'
        return base

    def _persist_to_db(self,level,message,extra):
        try:
            from .models import LogEntry
        except Exception:
            return

        try:
            merged = {**self.context,**extra}
            masked_context = self._mask_dict(data=merged)
            LogEntry.objects.create(
                level = level,
                logger_name=self.name,
                message = message,
                context = masked_context,
            )
        except Exception:
            pass

    def _write_to_file(self,formatted_line):
        try:
            directory = os.path.dirname(self.log_file)
            if directory:
                os.makedirs(directory, exist_ok=True)
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(formatted_line + "\n")
        except Exception as exc:
            sys.stderr.write(f"[django_view_logger] Fayla yazma xətası: {exc!r}\n")

    def _write(self, level, message, extra):
        if not self._is_enabled(level):
            return

        formatted = self._format_message(level, message, extra)
        stream = sys.stderr if level in STDERR_LEVELS else sys.stdout
        stream.write(formatted + "\n")
        stream.flush()

        if self.log_file:
            self._write_to_file(formatted)

        if self.db_log:
            self._persist_to_db(level,message,extra)


    def bind(self,**extra):
        new_context = {**self.context,**extra}
        return self.__class__(
            name = self.name,
            context = new_context,
            min_level = self.min_level,
            db_log=self.db_log,
            log_file = self.log_file
        )

    def debug(self, message, **extra):
        self._write("DEBUG", message, extra)

    def info(self, message, **extra):
        self._write("INFO", message, extra)

    def success(self, message, **extra):
        self._write("SUCCESS", message, extra)

    def warning(self, message, **extra):
        self._write("WARNING", message, extra)

    def error(self, message, **extra):
        self._write("ERROR", message, extra)

    def critical(self, message, **extra):
        self._write("CRITICAL", message, extra)

    def exception(self,message,exc=None,**extra):
        if exc is not None:
            extra=dict(extra)
            extra["exception_type"] = type(exc).__name__ # type(exc)-> <class 'ZeroDivisionError'> , __name__ -> ZeroDivisionError
            extra["exception_message"] = str(exc)

        self._write("ERROR", message, extra)

        tb = traceback.format_exc()
        if tb and tb.strip() != "NoneType: None":
            sys.stderr.write(tb+'\n')
            sys.stderr.flush()
