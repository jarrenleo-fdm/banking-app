"""MCP tests for API-key-only authentication."""
from decimal import Decimal

import pytest
from django.utils import timezone


@pytest.mark.django_db
def test_login_with_api_key_returns_session_token(db_user, make_api_key):
    from mcp_server.server import login_with_api_key

    api_key, raw_secret = make_api_key(db_user, "Claude Desktop")

    result = login_with_api_key(raw_secret)

    assert "session_token" in result
    assert len(result["session_token"]) == 64
    assert result["expires_in_minutes"] == 15
    assert result["username"] == "alice"
    assert result["auth_method"] == "api_key"
    assert result["api_key_identifier"] == api_key.identifier


@pytest.mark.django_db
def test_login_with_api_key_rejects_invalid_key():
    from mcp_server.server import login_with_api_key

    result = login_with_api_key("ak_0000000000000000.not-the-secret")

    assert result == {"error": "Authentication failed."}


@pytest.mark.django_db
def test_login_with_api_key_rejects_malformed_key():
    from mcp_server.server import login_with_api_key

    result = login_with_api_key("not-a-valid-key")

    assert result == {"error": "Authentication failed."}


@pytest.mark.django_db
def test_login_with_api_key_rejects_revoked_key(db_user, make_api_key):
    from mcp_server.server import login_with_api_key

    api_key, raw_secret = make_api_key(db_user, "Claude Desktop")
    api_key.revoked_at = timezone.now()
    api_key.save(update_fields=["revoked_at"])

    result = login_with_api_key(raw_secret)

    assert result == {"error": "Authentication failed."}


@pytest.mark.django_db
def test_revoked_api_key_session_rejects_protected_action(db_user, make_api_key):
    from mcp_server.server import deposit_funds, login_with_api_key

    api_key, raw_secret = make_api_key(db_user, "Claude Desktop")
    token = login_with_api_key(raw_secret)["session_token"]
    api_key.revoked_at = timezone.now()
    api_key.save(update_fields=["revoked_at"])

    result = deposit_funds("100.00", token)

    assert result == {"error": "Session expired or invalid. Please log in again."}
    db_user.account.refresh_from_db()
    assert db_user.account.balance == Decimal("0.00")


def test_username_password_login_is_unavailable():
    import mcp_server.server as server

    assert not hasattr(server, "login")
