"""
django_view_logger
===================

Sıfırdan hazırlanmış, heç bir standart ``logging`` modulundan asılı
olmayan, reusable Django View Logger.

İstifadə:

    from django_view_logger import BaseLogger, ViewLogger

Bax: README.md
"""

from .base import BaseLogger
from .view_logger import ViewLogger, get_current_request_id

__all__ = [
    "BaseLogger",
    "ViewLogger",
    "get_current_request_id",
]

__version__ = "1.0.0"
