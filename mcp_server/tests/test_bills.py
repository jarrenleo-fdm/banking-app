"""Tests for list_billers and pay_bill tools (US5)."""
from decimal import Decimal

import pytest

from banking import services


def _issue_token(username):
    from mcp_server.auth import token_store
    return token_store.issue_token(username)


@pytest.mark.django_db
class TestListBillers:
    def test_returns_biller_details(self, db_user, db_biller):
        from mcp_server.server import list_billers

        result = list_billers(username="alice")
        assert result["count"] == 1
        biller = result["billers"][0]
        assert biller["category"] == "ELECTRICITY"
        assert biller["category_display"] == "Electricity"
        assert biller["reference"] == "ACC-123456"
        assert "id" in biller
        assert "created_at" in biller

    def test_empty_account_returns_zero_count(self, db_user):
        from mcp_server.server import list_billers

        result = list_billers(username="alice")
        assert result == {"billers": [], "count": 0}

    def test_no_session_token_required(self, db_user, db_biller):
        from mcp_server.server import list_billers

        result = list_billers(username="alice")
        assert "error" not in result

    def test_unknown_username_returns_error(self):
        from mcp_server.server import list_billers

        result = list_billers(username="nobody")
        assert "error" in result


@pytest.mark.django_db
class TestPayBill:
    def test_valid_payment(self, db_user, db_biller):
        from mcp_server.server import pay_bill

        services.deposit(db_user.account, Decimal("500.00"))
        token = _issue_token("alice")
        result = pay_bill(
            username="alice",
            biller_id=db_biller.pk,
            amount="100.00",
            session_token=token,
        )
        assert result["new_balance"] == "400.00"
        assert "transaction_id" in result

    def test_biller_not_found_returns_error(self, db_user):
        from mcp_server.server import pay_bill

        token = _issue_token("alice")
        result = pay_bill("alice", 99999, "10.00", token)
        assert result == {"error": "Biller not found."}

    def test_biller_belongs_to_other_account_returns_error(
        self, db_user, db_recipient, db_biller
    ):
        from mcp_server.server import pay_bill

        # db_biller belongs to alice; bob cannot use it
        services.deposit(db_recipient.account, Decimal("500.00"))
        token = _issue_token("bob")
        result = pay_bill("bob", db_biller.pk, "10.00", token)
        assert result == {"error": "Biller not found."}

    def test_insufficient_funds_returns_error(self, db_user, db_biller):
        from mcp_server.server import pay_bill

        token = _issue_token("alice")
        result = pay_bill("alice", db_biller.pk, "999.00", token)
        assert result == {"error": "Insufficient funds."}

    def test_expired_token_returns_session_error(self, db_user, db_biller):
        from mcp_server.server import pay_bill

        result = pay_bill("alice", db_biller.pk, "10.00", "d" * 64)
        assert result == {"error": "Session expired or invalid. Please log in again."}

    def test_wrong_owner_returns_not_authorised(self, db_user, db_recipient, db_biller):
        from mcp_server.server import pay_bill

        token = _issue_token("bob")
        result = pay_bill("alice", db_biller.pk, "10.00", token)
        assert result == {"error": "Not authorised to perform this action."}

    def test_invalid_amount_returns_error(self, db_user, db_biller):
        from mcp_server.server import pay_bill

        token = _issue_token("alice")
        result = pay_bill("alice", db_biller.pk, "0.00", token)
        assert "error" in result
