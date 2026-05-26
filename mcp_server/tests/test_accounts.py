"""Tests for get_account and get_business_account tools (US1)."""
import pytest


@pytest.mark.django_db
class TestGetAccount:
    def test_valid_username_returns_account(self, db_user):
        from mcp_server.server import get_account

        result = get_account(username="alice")
        assert result["username"] == "alice"
        assert result["name"] == "Alice Tan"
        assert result["balance"] == "0.00"
        assert "created_at" in result
        # ISO 8601 — contains a T separator
        assert "T" in result["created_at"]

    def test_balance_is_string_not_float(self, db_user):
        from mcp_server.server import get_account

        result = get_account(username="alice")
        assert isinstance(result["balance"], str)

    def test_unknown_username_returns_error(self):
        from mcp_server.server import get_account

        result = get_account(username="nobody")
        assert "error" in result

    def test_no_session_token_required(self, db_user):
        from mcp_server.server import get_account

        # Must succeed without any token argument
        result = get_account(username="alice")
        assert "error" not in result


@pytest.mark.django_db
class TestGetBusinessAccount:
    def test_lookup_by_uen(self, db_business):
        from mcp_server.server import get_business_account

        result = get_business_account(identifier="202312345A")
        assert result["company_name"] == "Acme Pte Ltd"
        assert result["uen"] == "202312345A"
        assert result["balance"] == "50000.00"
        assert result["address"] == "10 Anson Road, Singapore 079903"

    def test_lookup_by_company_name_case_insensitive(self, db_business):
        from mcp_server.server import get_business_account

        result = get_business_account(identifier="acme pte ltd")
        assert result["uen"] == "202312345A"

    def test_includes_manager_and_authoriser(self, db_business):
        from mcp_server.server import get_business_account

        result = get_business_account(identifier="202312345A")
        assert result["manager"]["username"] == "manager.acme"
        assert result["authoriser"]["username"] == "authoriser.acme"

    def test_balance_is_string(self, db_business):
        from mcp_server.server import get_business_account

        result = get_business_account(identifier="202312345A")
        assert isinstance(result["balance"], str)

    def test_unknown_identifier_returns_error(self):
        from mcp_server.server import get_business_account

        result = get_business_account(identifier="UNKNOWN")
        assert "error" in result
