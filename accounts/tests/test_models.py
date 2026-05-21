"""Tests for custom user model and manager behavior."""
from decimal import Decimal

import pytest
from django.contrib.auth.hashers import identify_hasher
from django.core.exceptions import ValidationError
from django.db import IntegrityError

from accounts.models import CustomUser


def create_user(**overrides):
    data = {
        "username": "Alice",
        "email": "Alice@Example.COM",
        "name": "Alice Example",
        "phone_number": "81234567",
        "password": "StrongerPass123",
    }
    data.update(overrides)
    return CustomUser.objects.create_user(**data)


def test_username_is_unique_case_insensitively():
    create_user(username="Alice")

    with pytest.raises(IntegrityError):
        create_user(
            username="alice",
            email="other@example.com",
            phone_number="91234567",
        )


@pytest.mark.parametrize("phone", ["81234567", "91234567"])
def test_phone_number_accepts_valid_singapore_mobile_numbers(phone):
    user = CustomUser(
        username=f"user{phone}",
        email=f"{phone}@example.com",
        name="Valid Phone",
        phone_number=phone,
    )

    user.full_clean(exclude=["password"])


@pytest.mark.parametrize("phone", ["12345678", "8123456", "+6581234567"])
def test_phone_number_rejects_invalid_formats(phone):
    user = CustomUser(
        username=f"user{phone}",
        email=f"{phone}@example.com",
        name="Invalid Phone",
        phone_number=phone,
    )

    with pytest.raises(ValidationError):
        user.full_clean(exclude=["password"])


def test_email_is_stored_lowercase():
    user = create_user(email="UPPER@Example.COM")

    assert user.email == "upper@example.com"


def test_duplicate_email_is_rejected():
    create_user(email="same@example.com")

    with pytest.raises(IntegrityError):
        create_user(
            username="Bob",
            email="same@example.com",
            phone_number="91234567",
        )


def test_duplicate_phone_number_is_rejected():
    create_user(phone_number="81234567")

    with pytest.raises(IntegrityError):
        create_user(
            username="Bob",
            email="bob@example.com",
            phone_number="81234567",
        )


def test_create_user_hashes_password_with_argon2():
    user = create_user(password="StrongerPass123")

    assert user.check_password("StrongerPass123")
    assert identify_hasher(user.password).algorithm == "argon2"


def test_create_superuser_sets_staff_and_superuser_flags():
    user = CustomUser.objects.create_superuser(
        username="Admin",
        email="admin@example.com",
        name="Admin Example",
        phone_number="91234567",
        password="StrongerPass123",
    )

    assert user.is_staff is True
    assert user.is_superuser is True


def test_creating_user_auto_creates_zero_balance_account():
    user = create_user()

    assert user.account.balance == Decimal("0.00")
