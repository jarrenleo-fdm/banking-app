"""Banking app configuration."""
from django.apps import AppConfig


class BankingConfig(AppConfig):
    """Configuration for banking app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "banking"
