"""Tests for the banking data model (revised model)."""
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError

from banking.models import (
    AccountManagerProfile,
    Authoriser,
    Biller,
    BusinessAccount,
    BusinessTransaction,
    PendingTransaction,
)

User = get_user_model()


def make_user(username="corp", phone="81234567"):
    return User.objects.create_user(
        username=username,
        email=f"{username}@example.com",
        name=username.title(),
        phone_number=phone,
        password="TestPass123!",
    )


def make_business_account(**overrides):
    defaults = {
        "company_name": "Acme Corp",
        "uen": "202512345A",
        "street": "1 Marina Boulevard",
        "city": "Singapore",
        "postal_code": "018989",
    }
    defaults.update(overrides)
    return BusinessAccount.objects.create(**defaults)


# --- BusinessAccount model ---

def test_business_account_default_balance_is_zero():
    ba = make_business_account()
    assert ba.balance == Decimal("0.00")


def test_business_account_uen_is_unique():
    make_business_account(uen="UEN001")
    with pytest.raises(IntegrityError):
        make_business_account(uen="UEN001", company_name="Beta")


def test_business_account_str_returns_company_name():
    ba = make_business_account(company_name="Test Corp")
    assert str(ba) == "Test Corp"


def test_business_account_has_address_fields():
    ba = make_business_account(
        street="10 Orchard Road",
        city="Singapore",
        postal_code="238888",
    )
    assert ba.street == "10 Orchard Road"
    assert ba.city == "Singapore"
    assert ba.postal_code == "238888"


# --- AccountManagerProfile model ---

def test_account_manager_profile_links_user_to_business_account():
    user = make_user()
    ba = make_business_account()
    profile = AccountManagerProfile.objects.create(user=user, business_account=ba)
    assert profile.user == user
    assert profile.business_account == ba


def test_account_manager_profile_is_one_to_one_per_business_account():
    user1 = make_user("manager1", "81234567")
    user2 = make_user("manager2", "91234567")
    ba = make_business_account()
    AccountManagerProfile.objects.create(user=user1, business_account=ba)
    with pytest.raises(IntegrityError):
        AccountManagerProfile.objects.create(user=user2, business_account=ba)


def test_account_manager_profile_accessible_via_manager_profile_on_user():
    user = make_user()
    ba = make_business_account()
    AccountManagerProfile.objects.create(user=user, business_account=ba)
    assert user.manager_profile.business_account == ba


# --- Authoriser model ---

def test_authoriser_links_user_to_business_account():
    user = make_user()
    ba = make_business_account()
    auth = Authoriser.objects.create(user=user, business_account=ba)
    assert auth.user == user
    assert auth.business_account == ba
    assert auth.assigned_at is not None


def test_authoriser_is_one_to_one_per_business_account():
    user1 = make_user("auth1", "81234567")
    user2 = make_user("auth2", "91234567")
    ba = make_business_account()
    Authoriser.objects.create(user=user1, business_account=ba)
    with pytest.raises(IntegrityError):
        Authoriser.objects.create(user=user2, business_account=ba)


def test_authoriser_accessible_via_authoriser_profile_on_user():
    user = make_user()
    ba = make_business_account()
    Authoriser.objects.create(user=user, business_account=ba)
    assert user.authoriser_profile.business_account == ba


def test_authoriser_accessible_via_authoriser_on_business_account():
    user = make_user()
    ba = make_business_account()
    Authoriser.objects.create(user=user, business_account=ba)
    assert ba.authoriser.user == user


# --- PendingTransaction model ---

def test_pending_transaction_default_status_is_pending():
    user = make_user()
    ba = make_business_account()
    AccountManagerProfile.objects.create(user=user, business_account=ba)
    pt = PendingTransaction(
        business_account=ba,
        transaction_type=PendingTransaction.WITHDRAWAL,
        amount="100.00",
    )
    assert pt.status == PendingTransaction.PENDING


def test_pending_transaction_has_required_fields():
    user = make_user()
    ba = make_business_account()
    AccountManagerProfile.objects.create(user=user, business_account=ba)
    pt = PendingTransaction.objects.create(
        business_account=ba,
        transaction_type=PendingTransaction.WITHDRAWAL,
        amount="500.00",
    )
    assert pt.business_account == ba
    assert pt.transaction_type == PendingTransaction.WITHDRAWAL
    assert pt.status == PendingTransaction.PENDING
    assert pt.created_at is not None
    assert pt.decided_at is None
    assert pt.decided_by is None


# --- BusinessTransaction model ---

def test_business_transaction_records_deposit():
    user = make_user()
    ba = make_business_account()
    AccountManagerProfile.objects.create(user=user, business_account=ba)
    bt = BusinessTransaction.objects.create(
        business_account=ba,
        transaction_type=BusinessTransaction.DEPOSIT,
        amount=Decimal("1000.00"),
        balance_after=Decimal("1000.00"),
    )
    bt.refresh_from_db()
    assert bt.transaction_type == BusinessTransaction.DEPOSIT
    assert bt.amount == Decimal("1000.00")
    assert bt.balance_after == Decimal("1000.00")
    assert bt.timestamp is not None


def test_business_transaction_ordered_newest_first():
    ba = make_business_account()
    bt1 = BusinessTransaction.objects.create(
        business_account=ba, transaction_type=BusinessTransaction.DEPOSIT,
        amount="100.00", balance_after="100.00",
    )
    bt2 = BusinessTransaction.objects.create(
        business_account=ba, transaction_type=BusinessTransaction.DEPOSIT,
        amount="200.00", balance_after="300.00",
    )
    txns = list(BusinessTransaction.objects.filter(business_account=ba))
    assert txns[0].pk == bt2.pk
    assert txns[1].pk == bt1.pk


# --- Biller model ---

def test_biller_str_returns_category_and_reference():
    user = make_user()
    biller = Biller.objects.create(
        account=user.account, name=Biller.ELECTRICITY, reference="ACC-001"
    )
    assert str(biller) == "Electricity (ACC-001)"


def test_biller_belongs_to_account():
    user = make_user()
    biller = Biller.objects.create(
        account=user.account, name=Biller.TELECOMMUNICATIONS, reference="REF-001"
    )
    assert biller.account == user.account
    assert user.account.billers.filter(pk=biller.pk).exists()


def test_biller_reference_is_mandatory():
    user = make_user()
    biller = Biller(account=user.account, name=Biller.WATER_UTILITIES, reference="")
    with pytest.raises(ValidationError):
        biller.full_clean()


def test_biller_categories_all_return_correct_display_labels():
    user = make_user()
    expected = [
        (Biller.ELECTRICITY, "Electricity"),
        (Biller.WATER_UTILITIES, "Water & Utilities"),
        (Biller.INTERNET_BROADBAND, "Internet & Broadband"),
        (Biller.TELECOMMUNICATIONS, "Telecommunications"),
        (Biller.TOWN_COUNCIL, "Town Council / Maintenance"),
    ]
    for stored_value, display_label in expected:
        biller = Biller.objects.create(
            account=user.account, name=stored_value, reference="REF-001"
        )
        assert str(biller) == f"{display_label} (REF-001)"


def test_biller_reference_unique_per_account_and_category():
    user = make_user()
    Biller.objects.create(
        account=user.account, name=Biller.ELECTRICITY, reference="ACC-001"
    )
    with pytest.raises(IntegrityError):
        Biller.objects.create(
            account=user.account, name=Biller.ELECTRICITY, reference="ACC-001"
        )


def test_biller_same_reference_allowed_across_categories():
    user = make_user()
    Biller.objects.create(
        account=user.account, name=Biller.ELECTRICITY, reference="ACC-001"
    )
    biller2 = Biller.objects.create(
        account=user.account, name=Biller.INTERNET_BROADBAND, reference="ACC-001"
    )
    assert biller2.pk is not None
