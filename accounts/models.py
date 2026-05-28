"""Custom authentication models."""
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.core.validators import RegexValidator
from django.db import models
from django.db.models import Q
from django.db.models.functions import Lower
from django.utils import timezone

from .managers import CustomUserManager


class CustomUser(AbstractBaseUser, PermissionsMixin):
    """Application user with unique username, email, and phone number."""

    username = models.CharField(max_length=150, unique=True)
    email = models.EmailField(unique=True)
    name = models.CharField(max_length=150)
    phone_number = models.CharField(
        max_length=8,
        unique=True,
        validators=[RegexValidator(r"^[89]\d{7}$")],
    )
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)

    objects = CustomUserManager()

    USERNAME_FIELD = "username"
    REQUIRED_FIELDS = ["email", "name", "phone_number"]

    class Meta:
        constraints = [
            models.UniqueConstraint(
                Lower("username"),
                name="unique_username_case_insensitive",
            )
        ]

    def save(self, *args, **kwargs):
        self.email = self.email.lower()
        self.phone_number = self.phone_number.replace(" ", "").replace("-", "")
        super().save(*args, **kwargs)

    def __str__(self):
        return str(self.username)


class AccountAPIKey(models.Model):
    """User-owned MCP API key metadata with hashed secret material."""

    ACTIVE_KEY_LIMIT = 5

    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name="api_keys",
    )
    name = models.CharField(max_length=80)
    identifier = models.CharField(max_length=32, unique=True)
    secret_hash = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    last_used_at = models.DateTimeField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                Lower("name"),
                "user",
                condition=Q(revoked_at__isnull=True),
                name="unique_active_api_key_name_per_user",
            )
        ]

    @property
    def is_active(self):
        return self.revoked_at is None

    @property
    def display_label(self):
        return f"{self.name} ({self.identifier})"

    @classmethod
    def active_count_for_user(cls, user):
        return cls.objects.filter(user=user, revoked_at__isnull=True).count()

    def __str__(self):
        return self.display_label


class APIKeyAuditEvent(models.Model):
    """Non-sensitive audit event for API key lifecycle and authentication."""

    CREATED = "CREATED"
    AUTH_SUCCESS = "AUTH_SUCCESS"
    AUTH_FAILURE = "AUTH_FAILURE"
    REVOKED = "REVOKED"

    ACTION_CHOICES = [
        (CREATED, "Created"),
        (AUTH_SUCCESS, "Authentication success"),
        (AUTH_FAILURE, "Authentication failure"),
        (REVOKED, "Revoked"),
    ]

    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"

    OUTCOME_CHOICES = [
        (SUCCESS, "Success"),
        (FAILURE, "Failure"),
    ]

    user = models.ForeignKey(
        CustomUser,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="api_key_audit_events",
    )
    api_key = models.ForeignKey(
        AccountAPIKey,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="audit_events",
    )
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    outcome = models.CharField(max_length=10, choices=OUTCOME_CHOICES)
    reason = models.CharField(max_length=80, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        username = self.user.username if self.user_id else "unknown"
        return f"{self.action} {self.outcome} for {username}"
