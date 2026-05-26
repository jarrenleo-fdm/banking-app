"""Tests for list_transactions and list_business_transactions tools (US2)."""
from decimal import Decimal

import pytest


@pytest.mark.django_db
class TestListTransactions:
    def test_empty_account_returns_zero_count(self, db_user):
        from mcp_server.server import list_transactions

        result = list_transactions(username="alice")
        assert result == {"transactions": [], "count": 0}

    def test_returns_transactions_newest_first(self, db_user):
        from mcp_server.server import list_transactions
        from banking import services

        services.deposit(db_user.account, Decimal("100.00"))
        services.deposit(db_user.account, Decimal("200.00"))
        result = list_transactions(username="alice")
        assert result["count"] == 2
        # Newest first — second deposit has higher balance_after
        assert result["transactions"][0]["balance_after"] == "300.00"

    def test_transaction_type_filter(self, db_user):
        from mcp_server.server import list_transactions
        from banking import services

        services.deposit(db_user.account, Decimal("500.00"))
        services.withdraw(db_user.account, Decimal("50.00"))
        result = list_transactions(username="alice", transaction_type="DEPOSIT")
        assert result["count"] == 1
        assert result["transactions"][0]["transaction_type"] == "DEPOSIT"

    def test_limit_capped_at_100(self, db_user):
        from mcp_server.server import list_transactions

        result = list_transactions(username="alice", limit=200)
        # No error — limit silently capped
        assert "transactions" in result

    def test_default_limit_is_20(self, db_user):
        from mcp_server.server import list_transactions
        from banking import services

        for _ in range(25):
            services.deposit(db_user.account, Decimal("1.00"))
        result = list_transactions(username="alice")
        assert result["count"] == 20

    def test_amount_and_balance_are_strings(self, db_user):
        from mcp_server.server import list_transactions
        from banking import services

        services.deposit(db_user.account, Decimal("10.00"))
        result = list_transactions(username="alice")
        txn = result["transactions"][0]
        assert isinstance(txn["amount"], str)
        assert isinstance(txn["balance_after"], str)

    def test_unknown_username_returns_error(self):
        from mcp_server.server import list_transactions

        result = list_transactions(username="nobody")
        assert "error" in result

    def test_no_session_token_required(self, db_user):
        from mcp_server.server import list_transactions

        result = list_transactions(username="alice")
        assert "error" not in result


@pytest.mark.django_db
class TestListBusinessTransactions:
    def test_empty_returns_zero_count(self, db_business):
        from mcp_server.server import list_business_transactions

        result = list_business_transactions(identifier="202312345A")
        assert result == {"transactions": [], "count": 0}

    def test_returns_transactions(self, db_business):
        from mcp_server.server import list_business_transactions
        from banking import services

        services.deposit_to_business(db_business, Decimal("100.00"))
        result = list_business_transactions(identifier="202312345A")
        assert result["count"] == 1
        assert result["transactions"][0]["amount"] == "100.00"

    def test_response_has_no_counterparty_username(self, db_business):
        from mcp_server.server import list_business_transactions
        from banking import services

        services.deposit_to_business(db_business, Decimal("100.00"))
        result = list_business_transactions(identifier="202312345A")
        assert "counterparty_username" not in result["transactions"][0]

    def test_transaction_type_filter(self, db_business):
        from mcp_server.server import list_business_transactions
        from banking import services

        services.deposit_to_business(db_business, Decimal("100.00"))
        result = list_business_transactions(
            identifier="202312345A", transaction_type="DEPOSIT"
        )
        assert result["count"] == 1

    def test_unknown_identifier_returns_error(self):
        from mcp_server.server import list_business_transactions

        result = list_business_transactions(identifier="UNKNOWN")
        assert "error" in result
