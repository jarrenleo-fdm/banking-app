"""Admin registration for account users."""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import CustomUser


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    """Basic admin for the custom user model."""

    model = CustomUser
    list_display = ("username", "email", "name", "phone_number", "is_staff")
    list_filter = ("is_staff", "is_active")
    ordering = ("username",)
    search_fields = ("username", "email", "name", "phone_number")
    fieldsets = (
        (None, {"fields": ("username", "password")}),
        ("Personal info", {"fields": ("name", "email", "phone_number")}),
        ("Permissions", {"fields": ("is_active", "is_staff", "is_superuser")}),
        ("Important dates", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "username",
                    "email",
                    "name",
                    "phone_number",
                    "password1",
                    "password2",
                ),
            },
        ),
    )
    readonly_fields = ("date_joined", "last_login")
