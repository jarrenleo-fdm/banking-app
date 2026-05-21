"""Tests for Account.account_type and BusinessProfile model."""
import pytest
from django.contrib.auth import get_user_model
from django.db import IntegrityError

from banking.models import Account, Biller, BusinessProfile

User = get_user_model()


def make_user(username="corp", phone="81234567"):
    return User.objects.create_user(
        username=username,
        email=f"{username}@example.com",
        name=username.title(),
        phone_number=phone,
        password="TestPass123!",
    )


def test_account_type_defaults_to_personal():
    user = make_user()
    assert user.account.account_type == Account.PERSONAL


def test_account_type_can_be_set_to_business():
    user = make_user()
    user.account.account_type = Account.BUSINESS
    user.account.save(update_fields=["account_type"])
    user.account.refresh_from_db()
    assert user.account.account_type == Account.BUSINESS


def test_business_profile_can_be_created():
    user = make_user()
    user.account.account_type = Account.BUSINESS
    user.account.save(update_fields=["account_type"])
    profile = BusinessProfile.objects.create(
        account=user.account,
        company_name="Acme Pte Ltd",
        business_registration_number="ABC12345",
    )
    assert profile.account == user.account
    assert profile.company_name == "Acme Pte Ltd"
    assert profile.business_registration_number == "ABC12345"


def test_business_registration_number_unique_constraint():
    user1 = make_user("corp1", "81234567")
    user2 = make_user("corp2", "91234567")
    user1.account.account_type = Account.BUSINESS
    user1.account.save(update_fields=["account_type"])
    user2.account.account_type = Account.BUSINESS
    user2.account.save(update_fields=["account_type"])

    BusinessProfile.objects.create(
        account=user1.account,
        company_name="Acme Pte Ltd",
        business_registration_number="ABC12345",
    )
    with pytest.raises(IntegrityError):
        BusinessProfile.objects.create(
            account=user2.account,
            company_name="Beta Corp",
            business_registration_number="ABC12345",
        )


# --- Biller model tests ---

def test_biller_str_returns_name():
    user = make_user()
    biller = Biller.objects.create(account=user.account, name="SP PowerGrid")
    assert str(biller) == "SP PowerGrid"


def test_biller_belongs_to_account():
    user = make_user()
    biller = Biller.objects.create(account=user.account, name="Starhub")
    assert biller.account == user.account
    assert user.account.billers.filter(pk=biller.pk).exists()


def test_biller_reference_can_be_blank():
    user = make_user()
    biller = Biller.objects.create(account=user.account, name="PUB", reference="")
    assert biller.reference == ""
