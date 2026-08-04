from django.db import models

class LogEntryQuerySet(models.QuerySet):
    def by_level(self,level):
        return self.filter(level=level)

    def by_logger(self,logger_name):
        return self.filter(logger_name=logger_name)

    def errors(self):
        return self.filter(level__in=["ERROR", "CRITICAL"])

class LogEntry(models.Model):
    LEVEL_CHOICES = [
        ("DEBUG", "DEBUG"),
        ("INFO", "INFO"),
        ("SUCCESS", "SUCCESS"),
        ("WARNING", "WARNING"),
        ("ERROR", "ERROR"),
        ("CRITICAL", "CRITICAL"),
    ]

    level = models.CharField(max_length=10, choices=LEVEL_CHOICES, db_index=True)
    logger_name = models.CharField(max_length=255, db_index=True)
    message = models.TextField()
    context = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    objects = LogEntryQuerySet.as_manager()

    class Meta:
        app_label = "logger"
        ordering = ["-created_at"]
        verbose_name = "Log Entry"
        verbose_name_plural = "Log Entries"
        indexes = [
            models.Index(fields=["level", "created_at"]),
            models.Index(fields=["logger_name", "created_at"]),
        ]

    def __str__(self):
        preview = self.message if len(self.message) < 50 else self.message[:50] + "..."
        return f"[{self.level}] {self.logger_name} - {preview}"