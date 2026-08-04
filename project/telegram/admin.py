from django.contrib import admin
from .models import TelegramUser


@admin.register(TelegramUser)
class TelegramUserAdmin(admin.ModelAdmin):
    # Cədvəldə görünəcək sütunlar
    list_display = (
        'telegram_id',
        'get_full_name',
        'username',
        'is_active',
        'created_at',  # Əgər BaseDatabaseModel-də vardan istifadə edə bilərsiniz
    )

    # Sütunlara basaraq filterləmə
    list_filter = (
        'is_active',
        'created_at',
    )

    # Axtarış xanasında axtarıla biləcək sahələr
    search_fields = (
        'telegram_id',
        'username',
        'first_name',
        'last_name',
    )

    # Düzəliş (Edit) səhifəsində sahələrin qruplaşdırılması
    fieldsets = (
        ('İstifadəçi Məlumatları', {
            'fields': ('telegram_id', 'username', 'first_name', 'last_name')
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
    )

    # Cədvəlin özündən is_active dəyərini tez dəyişmək üçün
    list_editable = ('is_active',)

    # Səhifələmə (Page size)
    list_per_page = 25

    # Oxunma rejimi (əgər telegram_id-nin əllə dəyişdirilməsini istəməsiniz)
    readonly_fields = ('telegram_id',)

    # Tam adı göstərən köməkçi metod
    @admin.display(description='Ad Soyad')
    def get_full_name(self, obj):
        full_name = f"{obj.first_name or ''} {obj.last_name or ''}".strip()
        return full_name if full_name else "-"

    # Massiv əməliyyatlar (Bulk actions) - Istifadəçiləri toplu aktiv/deaktiv etmək üçün
    actions = ['make_active', 'make_inactive']

    @admin.action(description='Seçilmiş istifadəçiləri aktiv et')
    def make_active(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f"{updated} istifadəçi aktiv edildi.")

    @admin.action(description='Seçilmiş istifadəçiləri deaktiv et')
    def make_inactive(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f"{updated} istifadəçi deaktiv edildi.")