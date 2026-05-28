"""Tests for protected personal money movement tools."""
from decimal import Decimal

import pytest

from banking.models import Transaction


@pytest.mark.django_db
class TestDepositFunds:
    def test_valid_deposit(self, db_user, api_session):
        from mcp_server.server import deposit_funds

        result = deposit_funds(amount="200.00", session_token=api_session)

        assert result["new_balance"] == "200.00"
        assert "transaction_id" in result
        db_user.account.refresh_from_db()
        assert db_user.account.balance == Decimal("200.00")

    def test_missing_token_returns_session_error(self, db_user):
        from mcp_server.server import deposit_funds

        result = deposit_funds("100.00", "")

        assert result == {"error": "Session expired or invalid. Please log in again."}

    def test_revoked_token_returns_session_error(self, db_user, revoked_api_session):
        from mcp_server.server import deposit_funds

        result = deposit_funds("100.00", revoked_api_session)

        assert result == {"error": "Session expired or invalid. Please log in again."}
        db_user.account.refresh_from_db()
        assert db_user.account.balance == Decimal("0.00")

    def test_invalid_amount_leaves_balance_unchanged(self, db_user, api_session):
        from mcp_server.server import deposit_funds

        result = deposit_funds("10.001", api_session)

        assert "error" in result
        db_user.account.refresh_from_db()
        assert db_user.account.balance == Decimal("0.00")


@pytest.mark.django_db
class TestWithdrawFunds:
    def test_valid_withdrawal(self, funded_user, api_session):
        from mcp_server.server import withdraw_funds

        result = withdraw_funds(amount="100.00", session_token=api_session)

        assert result["new_balance"] == "400.00"
        assert "transaction_id" in result

    def test_insufficient_funds_leaves_balance_unchanged(self, db_user, api_session):
        from mcp_server.server import withdraw_funds

        result = withdraw_funds("999.00", api_session)

        assert result == {"error": "Insufficient funds."}
        db_user.account.refresh_from_db()
        assert db_user.account.balance == Decimal("0.00")

    def test_invalid_amount_leaves_balance_unchanged(self, db_user, api_session):
        from mcp_server.server import withdraw_funds

        result = withdraw_funds("-50.00", api_session)

        assert "error" in result
        db_user.account.refresh_from_db()
        assert db_user.account.balance == Decimal("0.00")

    def test_missing_token_returns_session_error(self, db_user):
        from mcp_server.server import withdraw_funds

        result = withdraw_funds("10.00", "")

        assert result == {"error": "Session expired or invalid. Please log in again."}

    def test_revoked_token_returns_session_error(self, db_user, revoked_api_session):
        from mcp_server.server import withdraw_funds

        result = withdraw_funds("10.00", revoked_api_session)

        assert result == {"error": "Session expired or invalid. Please log in again."}


@pytest.mark.django_db
class TestTransferFunds:
    def test_valid_transfer_by_phone_with_description(
        self, funded_user, db_recipient, api_session
    ):
        from mcp_server.server import transfer_funds

        result = transfer_funds(
            recipient_phone="91234567",
            amount="50.00",
            session_token=api_session,
            description="Lunch split",
        )

        assert result["sender_new_balance"] == "450.00"
        assert "out_transaction_id" in result
        assert "in_transaction_id" in result
        funded_user.account.refresh_from_db()
        db_recipient.account.refresh_from_db()
        assert funded_user.account.balance == Decimal("450.00")
        assert db_recipient.account.balance == Decimal("50.00")
        assert Transaction.objects.get(
            pk=result["out_transaction_id"]
        ).description == "Lunch split"
        assert Transaction.objects.get(
            pk=result["in_transaction_id"]
        ).description == "Lunch split"

    def test_missing_recipient_leaves_balance_unchanged(self, funded_user, api_session):
        from mcp_server.server import transfer_funds

        result = transfer_funds("99999999", "10.00", api_session)

        assert result == {"error": "Recipient not found."}
        funded_user.account.refresh_from_db()
        assert funded_user.account.balance == Decimal("500.00")

    def test_self_transfer_rejected(self, funded_user, api_session):
        from mcp_server.server import transfer_funds

        result = transfer_funds("81234567", "10.00", api_session)

        assert result == {"error": "Cannot transfer to your own account."}

    def test_insufficient_funds_leaves_balance_unchanged(
        self, db_user, db_recipient, api_session
    ):
        from mcp_server.server import transfer_funds

        result = transfer_funds("91234567", "999.00", api_session)

        assert result == {"error": "Insufficient funds."}
        db_user.account.refresh_from_db()
        db_recipient.account.refresh_from_db()
        assert db_user.account.balance == Decimal("0.00")
        assert db_recipient.account.balance == Decimal("0.00")

    def test_invalid_amount_leaves_balance_unchanged(
        self, db_user, db_recipient, api_session
    ):
        from mcp_server.server import transfer_funds

        result = transfer_funds("91234567", "0.00", api_session)

        assert "error" in result
        db_user.account.refresh_from_db()
        db_recipient.account.refresh_from_db()
        assert db_user.account.balance == Decimal("0.00")
        assert db_recipient.account.balance == Decimal("0.00")

    def test_missing_token_returns_session_error(self, db_recipient):
        from mcp_server.server import transfer_funds

        result = transfer_funds("91234567", "10.00", "")

        assert result == {"error": "Session expired or invalid. Please log in again."}

    def test_description_too_long_returns_error(
        self, funded_user, db_recipient, api_session
    ):
        from mcp_server.server import transfer_funds

        result = transfer_funds("91234567", "10.00", api_session, description="x" * 201)

        assert result == {"error": "Description must be 200 characters or fewer."}
        funded_user.account.refresh_from_db()
        assert funded_user.account.balance == Decimal("500.00")
