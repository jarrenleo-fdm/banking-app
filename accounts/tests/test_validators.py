"""Unit tests for custom password validators."""
import pytest
from django.core.exceptions import ValidationError

from accounts.validators import PasswordComplexityValidator


@pytest.fixture
def validator():
    return PasswordComplexityValidator()


def test_valid_complex_password_passes(validator):
    validator.validate("StrongerPass123!")


def test_missing_uppercase_raises(validator):
    with pytest.raises(ValidationError, match="uppercase"):
        validator.validate("strongerpass123!")


def test_missing_lowercase_raises(validator):
    with pytest.raises(ValidationError, match="lowercase"):
        validator.validate("STRONGERPASS123!")


def test_missing_digit_raises(validator):
    with pytest.raises(ValidationError, match="digit"):
        validator.validate("StrongerPass!")


def test_missing_special_char_raises(validator):
    with pytest.raises(ValidationError, match="special"):
        validator.validate("StrongerPass123")


def test_get_help_text_mentions_all_criteria(validator):
    text = validator.get_help_text()
    assert "uppercase" in text
    assert "lowercase" in text
    assert "digit" in text
    assert "special" in text
