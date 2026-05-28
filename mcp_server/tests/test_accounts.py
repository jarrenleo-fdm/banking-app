"""Tests for protected get_account tool."""
import inspect

import pytest


@pytest.mark.django_db
class TestGetAccount:
    def test_valid_session_returns_authenticated_account(self, db_user, api_session):
        from mcp_server.server import get_account

        result = get_account(session_token=api_session)

        assert result["username"] == "alice"
        assert result["name"] == "Alice Tan"
        assert result["phone_number"] == "81234567"
        assert result["balance"] == "0.00"
        assert isinstance(result["balance"], str)
        assert "T" in result["created_at"]

    def test_missing_session_token_returns_session_error(self, db_user):
        from mcp_server.server import get_account

        result = get_account(session_token="")

        assert result == {"error": "Session expired or invalid. Please log in again."}

    def test_revoked_session_returns_session_error(self, db_user, revoked_api_session):
        from mcp_server.server import get_account

        result = get_account(session_token=revoked_api_session)

        assert result == {"error": "Session expired or invalid. Please log in again."}

    def test_tool_does_not_accept_username_target(self):
        from mcp_server.server import get_account

        assert list(inspect.signature(get_account).parameters) == ["session_token"]
