"""Custom user manager for email normalization and superuser creation."""
from django.contrib.auth.base_user import BaseUserManager


class CustomUserManager(BaseUserManager):
    """Manager for CustomUser using username as the login identifier."""

    def create_user(self, username, email, name, phone_number, password=None, **extra):
        """Create and save a regular user."""
        if not username:
            raise ValueError("The username must be set")
        if not email:
            raise ValueError("The email must be set")

        email = self.normalize_email(email).lower()
        user = self.model(
            username=username,
            email=email,
            name=name,
            phone_number=phone_number,
            **extra,
        )
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(
        self, username, email, name, phone_number, password=None, **extra
    ):
        """Create and save a superuser."""
        extra.setdefault("is_staff", True)
        extra.setdefault("is_superuser", True)
        extra.setdefault("is_active", True)

        if extra.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self.create_user(username, email, name, phone_number, password, **extra)
