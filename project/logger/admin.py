from django.contrib import admin

from .models import LogEntry


@admin.register(LogEntry)
class LogEntryAdmin(admin.ModelAdmin):
    list_display = ("id", "level", "logger_name", "short_message", "created_at")
    list_filter = ("level", "logger_name")
    search_fields = ("message", "logger_name")
    readonly_fields = ("level", "logger_name", "message", "context", "created_at")
    ordering = ("-created_at",)
    date_hierarchy = "created_at"

    def short_message(self, obj):
        return obj.message if len(obj.message) <= 80 else obj.message[:80] + "..."

    short_message.short_description = "Message"

    def has_add_permission(self, request):
        # Loglar yalnız kod tərəfindən yaradılır, admin-dən əl ilə əlavə edilməməlidir
        return False