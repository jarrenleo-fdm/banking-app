"""Admin registration for account users."""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import APIKeyAuditEvent, AccountAPIKey, CustomUser


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


@admin.register(AccountAPIKey)
class AccountAPIKeyAdmin(admin.ModelAdmin):
    """Metadata-only API key admin; raw secrets and hashes are not displayed."""

    list_display = (
        "name",
        "identifier",
        "user",
        "created_at",
        "last_used_at",
        "revoked_at",
    )
    list_filter = ("created_at", "last_used_at", "revoked_at")
    search_fields = ("name", "identifier", "user__username", "user__email")
    readonly_fields = (
        "user",
        "name",
        "identifier",
        "created_at",
        "last_used_at",
        "revoked_at",
    )
    exclude = ("secret_hash",)

    def has_add_permission(self, request):
        return False


@admin.register(APIKeyAuditEvent)
class APIKeyAuditEventAdmin(admin.ModelAdmin):
    """Read-only audit view for API key security events."""

    list_display = ("action", "outcome", "user", "api_key", "reason", "created_at")
    list_filter = ("action", "outcome", "created_at")
    search_fields = ("user__username", "api_key__identifier", "reason")
    readonly_fields = ("user", "api_key", "action", "outcome", "reason", "created_at")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
