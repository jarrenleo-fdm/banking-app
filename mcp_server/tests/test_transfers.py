"""Tests for transfer_funds, deposit_funds, and withdraw_funds tools (US3/US4)."""
from decimal import Decimal

import pytest

from banking import services


def _issue_token(username):
    from mcp_server.auth import token_store
    return token_store.issue_token(username)


@pytest.mark.django_db
class TestTransferFunds:
    def test_valid_transfer(self, db_user, db_recipient):
        from mcp_server.server import transfer_funds

        services.deposit(db_user.account, Decimal("200.00"))
        token = _issue_token("alice")
        result = transfer_funds(
            from_username="alice",
            to_username="bob",
            amount="50.00",
            session_token=token,
        )
        assert "sender_new_balance" in result
        assert result["sender_new_balance"] == "150.00"
        assert "out_transaction_id" in result
        assert "in_transaction_id" in result

    def test_insufficient_funds_returns_error(self, db_user, db_recipient):
        from mcp_server.server import transfer_funds

        token = _issue_token("alice")
        result = transfer_funds("alice", "bob", "999.00", token)
        assert "error" in result
        # Balance unchanged
        db_user.account.refresh_from_db()
        assert db_user.account.balance == Decimal("0.00")

    def test_unknown_recipient_returns_error(self, db_user):
        from mcp_server.server import transfer_funds

        services.deposit(db_user.account, Decimal("100.00"))
        token = _issue_token("alice")
        result = transfer_funds("alice", "nobody", "10.00", token)
        assert "error" in result

    def test_expired_token_returns_session_error(self, db_user, db_recipient):
        from mcp_server.server import transfer_funds

        result = transfer_funds("alice", "bob", "10.00", "a" * 64)
        assert result == {"error": "Session expired or invalid. Please log in again."}

    def test_wrong_owner_token_returns_not_authorised(self, db_user, db_recipient):
        from mcp_server.server import transfer_funds

        token = _issue_token("bob")
        services.deposit(db_user.account, Decimal("100.00"))
        result = transfer_funds("alice", "bob", "10.00", token)
        assert result == {"error": "Not authorised to perform this action."}

    def test_zero_amount_returns_validation_error(self, db_user, db_recipient):
        from mcp_server.server import transfer_funds

        token = _issue_token("alice")
        result = transfer_funds("alice", "bob", "0", token)
        assert "error" in result

    def test_three_decimal_places_returns_validation_error(self, db_user, db_recipient):
        from mcp_server.server import transfer_funds

        token = _issue_token("alice")
        result = transfer_funds("alice", "bob", "10.001", token)
        assert "error" in result


@pytest.mark.django_db
class TestDepositFunds:
    def test_valid_deposit(self, db_user):
        from mcp_server.server import deposit_funds

        token = _issue_token("alice")
        result = deposit_funds(username="alice", amount="200.00", session_token=token)
        assert result["new_balance"] == "200.00"
        assert "transaction_id" in result

    def test_zero_amount_returns_error(self, db_user):
        from mcp_server.server import deposit_funds

        token = _issue_token("alice")
        result = deposit_funds("alice", "0.00", token)
        assert "error" in result

    def test_expired_token_returns_session_error(self, db_user):
        from mcp_server.server import deposit_funds

        result = deposit_funds("alice", "100.00", "b" * 64)
        assert result == {"error": "Session expired or invalid. Please log in again."}

    def test_wrong_owner_returns_not_authorised(self, db_user, db_recipient):
        from mcp_server.server import deposit_funds

        token = _issue_token("bob")
        result = deposit_funds("alice", "100.00", token)
        assert result == {"error": "Not authorised to perform this action."}

    def test_unknown_account_returns_error(self):
        from mcp_server.server import deposit_funds

        token = _issue_token("ghost")
        result = deposit_funds("ghost", "100.00", token)
        assert "error" in result


@pytest.mark.django_db
class TestWithdrawFunds:
    def test_valid_withdrawal(self, db_user):
        from mcp_server.server import withdraw_funds

        services.deposit(db_user.account, Decimal("500.00"))
        token = _issue_token("alice")
        result = withdraw_funds(username="alice", amount="100.00", session_token=token)
        assert result["new_balance"] == "400.00"
        assert "transaction_id" in result

    def test_insufficient_funds_returns_error(self, db_user):
        from mcp_server.server import withdraw_funds

        token = _issue_token("alice")
        result = withdraw_funds("alice", "999.00", token)
        assert result == {"error": "Insufficient funds."}

    def test_wrong_owner_returns_not_authorised(self, db_user, db_recipient):
        from mcp_server.server import withdraw_funds

        token = _issue_token("bob")
        result = withdraw_funds("alice", "10.00", token)
        assert result == {"error": "Not authorised to perform this action."}

    def test_expired_token_returns_session_error(self, db_user):
        from mcp_server.server import withdraw_funds

        result = withdraw_funds("alice", "10.00", "c" * 64)
        assert result == {"error": "Session expired or invalid. Please log in again."}

    def test_negative_amount_returns_error(self, db_user):
        from mcp_server.server import withdraw_funds

        token = _issue_token("alice")
        result = withdraw_funds("alice", "-50.00", token)
        assert "error" in result
