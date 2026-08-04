from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import CustomUser


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    model = CustomUser

    list_display = (
        'email',
        'username',
        'phone_number',
        'is_staff',
        'is_active',
    )

    list_display_links = (
        'email',
    )

    list_filter = (
        'is_staff',
        'is_active',
        'is_superuser',
        'groups',
    )

    ordering = ('email',)
    search_fields = ('email', 'username', 'phone_number')

    fieldsets = (
        (None, {
            'fields': ('email', 'password')
        }),
        ('Personal info', {
            'fields': (
                'username',
                'first_name',
                'last_name',
                'bio',
                'phone_number',
                'profile_picture',
            )
        }),
        ('Permissions', {
            'fields': (
                'is_active',
                'is_staff',
                'is_superuser',
                'groups',
                'user_permissions',
            )
        }),
        ('Important dates', {
            'fields': (
                'last_login',
                'date_joined',
                'password_change_count',
                'password_change_date',
            )
        }),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': (
                'email',
                'username',
                'password1',
                'password2',
                'is_staff',
                'is_active',
            ),
        }),
    )