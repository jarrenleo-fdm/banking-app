"""Shared fixtures for mcp_server tests."""
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model

from accounts.api_keys import create_key, revoke_key
from banking import services
from banking.models import Biller

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
def db_other(db):
    return User.objects.create_user(
        username="charlie",
        email="charlie@example.com",
        name="Charlie Goh",
        phone_number="91230000",
        password="TestPass123!",
    )


@pytest.fixture
def db_biller(db, db_user):
    return Biller.objects.create(
        account=db_user.account,
        name=Biller.ELECTRICITY,
        reference="ACC-123456",
    )


@pytest.fixture
def db_bob_biller(db, db_recipient):
    return Biller.objects.create(
        account=db_recipient.account,
        name=Biller.TELECOMMUNICATIONS,
        reference="BOB-123456",
    )


@pytest.fixture
def make_api_key(db):
    def _make(user, name="Test MCP Client"):
        return create_key(user, name)

    return _make


@pytest.fixture
def make_api_session(db, make_api_key):
    def _make(user, name="Test MCP Client"):
        api_key, _raw_secret = make_api_key(user, name)
        from mcp_server.auth import token_store

        token = token_store.issue_token(
            user.username,
            api_key_identifier=api_key.identifier,
        )
        return token, api_key

    return _make


@pytest.fixture
def api_session(db_user, make_api_session):
    token, _api_key = make_api_session(db_user)
    return token


@pytest.fixture
def revoked_api_session(db_user, make_api_session):
    token, api_key = make_api_session(db_user, "Revoked Client")
    revoke_key(api_key, db_user)
    return token


@pytest.fixture
def funded_user(db_user):
    services.deposit(db_user.account, Decimal("500.00"))
    db_user.account.refresh_from_db()
    return db_user
