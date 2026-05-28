"""Tests for protected biller and bill-payment MCP tools."""
from decimal import Decimal

import pytest

from banking.models import Biller


@pytest.mark.django_db
class TestListBillers:
    def test_returns_authenticated_users_biller_details(
        self, db_user, db_biller, api_session
    ):
        from mcp_server.server import list_billers

        result = list_billers(session_token=api_session)

        assert result["count"] == 1
        biller = result["billers"][0]
        assert biller["category"] == "ELECTRICITY"
        assert biller["category_display"] == "Electricity"
        assert biller["reference"] == "ACC-123456"
        assert "id" in biller
        assert "created_at" in biller

    def test_empty_account_returns_zero_count(self, db_user, api_session):
        from mcp_server.server import list_billers

        result = list_billers(session_token=api_session)

        assert result == {"billers": [], "count": 0}

    def test_missing_session_token_returns_session_error(self, db_user):
        from mcp_server.server import list_billers

        result = list_billers(session_token="")

        assert result == {"error": "Session expired or invalid. Please log in again."}

    def test_revoked_session_returns_session_error(self, revoked_api_session):
        from mcp_server.server import list_billers

        result = list_billers(session_token=revoked_api_session)

        assert result == {"error": "Session expired or invalid. Please log in again."}

    def test_does_not_return_another_users_billers(
        self, db_user, db_bob_biller, api_session
    ):
        from mcp_server.server import list_billers

        result = list_billers(session_token=api_session)

        assert result == {"billers": [], "count": 0}


@pytest.mark.django_db
class TestAddBiller:
    def test_valid_biller_is_saved(self, db_user, api_session):
        from mcp_server.server import add_biller

        result = add_biller(api_session, Biller.ELECTRICITY, "ACC-123")

        assert result["category"] == "ELECTRICITY"
        assert result["category_display"] == "Electricity"
        assert result["reference"] == "ACC-123"
        assert "id" in result
        assert "created_at" in result
        assert db_user.account.billers.count() == 1

    def test_invalid_category_returns_error(self, db_user, api_session):
        from mcp_server.server import add_biller

        result = add_biller(api_session, "INVALID", "ACC-123")

        assert result == {
            "error": (
                "Invalid category. Must be one of: ELECTRICITY, WATER_UTILITIES, "
                "INTERNET_BROADBAND, TELECOMMUNICATIONS, TOWN_COUNCIL."
            )
        }

    def test_blank_reference_returns_error(self, db_user, api_session):
        from mcp_server.server import add_biller

        result = add_biller(api_session, Biller.ELECTRICITY, " ")

        assert result == {"error": "Reference is required."}

    def test_duplicate_category_and_reference_returns_error(
        self, db_user, db_biller, api_session
    ):
        from mcp_server.server import add_biller

        result = add_biller(api_session, Biller.ELECTRICITY, "ACC-123456")

        assert result == {
            "error": "A biller with this category and reference already exists."
        }
        assert db_user.account.billers.count() == 1

    def test_missing_token_returns_session_error(self, db_user):
        from mcp_server.server import add_biller

        result = add_biller("", Biller.ELECTRICITY, "ACC-123")

        assert result == {"error": "Session expired or invalid. Please log in again."}

    def test_revoked_token_returns_session_error(self, revoked_api_session):
        from mcp_server.server import add_biller

        result = add_biller(revoked_api_session, Biller.ELECTRICITY, "ACC-123")

        assert result == {"error": "Session expired or invalid. Please log in again."}


@pytest.mark.django_db
class TestPayBill:
    def test_valid_payment(self, funded_user, db_biller, api_session):
        from mcp_server.server import pay_bill

        result = pay_bill(
            biller_id=db_biller.pk,
            amount="100.00",
            session_token=api_session,
        )

        assert result["new_balance"] == "400.00"
        assert "transaction_id" in result

    def test_biller_not_found_returns_error(self, db_user, api_session):
        from mcp_server.server import pay_bill

        result = pay_bill(99999, "10.00", api_session)

        assert result == {"error": "Biller not found."}

    def test_biller_belongs_to_other_account_returns_error(
        self, db_user, db_bob_biller, api_session
    ):
        from mcp_server.server import pay_bill

        result = pay_bill(db_bob_biller.pk, "10.00", api_session)

        assert result == {"error": "Biller not found."}

    def test_insufficient_funds_returns_error(self, db_user, db_biller, api_session):
        from mcp_server.server import pay_bill

        result = pay_bill(db_biller.pk, "999.00", api_session)

        assert result == {"error": "Insufficient funds."}
        db_user.account.refresh_from_db()
        assert db_user.account.balance == Decimal("0.00")

    def test_invalid_amount_returns_error(self, db_user, db_biller, api_session):
        from mcp_server.server import pay_bill

        result = pay_bill(db_biller.pk, "0.00", api_session)

        assert "error" in result

    def test_missing_token_returns_session_error(self, db_biller):
        from mcp_server.server import pay_bill

        result = pay_bill(db_biller.pk, "10.00", "")

        assert result == {"error": "Session expired or invalid. Please log in again."}

    def test_revoked_token_returns_session_error(self, db_biller, revoked_api_session):
        from mcp_server.server import pay_bill

        result = pay_bill(db_biller.pk, "10.00", revoked_api_session)

        assert result == {"error": "Session expired or invalid. Please log in again."}
