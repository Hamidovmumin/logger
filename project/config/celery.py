import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

app = Celery("config")

app.config_from_object("django.conf:settings", namespace="CELERY")

# Django app-ların tasks.py fayllarını tapır
app.autodiscover_tasks()


app.conf.imports = (
    "scrape.tasks",
    "scrape.message_bot",
)