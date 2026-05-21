"""Custom authentication models."""
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.core.validators import RegexValidator
from django.db import models
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
