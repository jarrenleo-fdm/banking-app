"""Custom password validators for the accounts app."""
import re

from django.core.exceptions import ValidationError


class PasswordComplexityValidator:
    """Requires uppercase, lowercase, digit, and special character."""

    def validate(self, password, user=None):
        errors = []
        if not re.search(r"[A-Z]", password):
            errors.append("at least one uppercase letter (A–Z)")
        if not re.search(r"[a-z]", password):
            errors.append("at least one lowercase letter (a–z)")
        if not re.search(r"\d", password):
            errors.append("at least one digit (0–9)")
        if not re.search(r"[^A-Za-z0-9]", password):
            errors.append("at least one special character")
        if errors:
            raise ValidationError(
                f"Password must contain {', '.join(errors)}.",
                code="password_complexity",
            )

    def get_help_text(self):
        return (
            "Your password must contain at least one uppercase letter (A–Z), "
            "one lowercase letter (a–z), one digit (0–9), "
            "and one special character."
        )
