"""Shared fixtures for mcp_server tests."""
import pytest
from django.contrib.auth import get_user_model

from banking.models import (
    AccountManagerProfile,
    Authoriser,
    Biller,
    BusinessAccount,
)

User = get_user_model()


@pytest.fixture(autouse=True)
def clear_token_store():
    """Reset in-memory token store between tests."""
    yield
    try:
        from mcp_server.auth import token_store

        token_store._tokens.clear()
    except (ImportError, AttributeError):
        pass


@pytest.fixture
def db_user(db):
    return User.objects.create_user(
        username="alice",
        email="alice@example.com",
        name="Alice Tan",
        phone_number="81234567",
        password="TestPass123!",
    )


@pytest.fixture
def db_recipient(db):
    return User.objects.create_user(
        username="bob",
        email="bob@example.com",
        name="Bob Lee",
        phone_number="91234567",
        password="TestPass123!",
    )


@pytest.fixture
def db_business(db):
    ba = BusinessAccount.objects.create(
        company_name="Acme Pte Ltd",
        uen="202312345A",
        street="10 Anson Road",
        city="Singapore",
        postal_code="079903",
        balance="50000.00",
    )
    manager_user = User.objects.create_user(
        username="manager.acme",
        email="manager.acme@demo.internal",
        name="Manager (Acme Pte Ltd)",
        phone_number="80000001",
        password="ManagerPass123!",
    )
    AccountManagerProfile.objects.create(user=manager_user, business_account=ba)

    authoriser_user = User.objects.create_user(
        username="authoriser.acme",
        email="authoriser.acme@demo.internal",
        name="Authoriser (Acme Pte Ltd)",
        phone_number="80000002",
        password="AuthPass123!",
    )
    Authoriser.objects.create(user=authoriser_user, business_account=ba)
    return ba


@pytest.fixture
def db_biller(db, db_user):
    return Biller.objects.create(
        account=db_user.account,
        name=Biller.ELECTRICITY,
        reference="ACC-123456",
    )
