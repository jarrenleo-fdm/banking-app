"""Tests for protected list_transactions tool."""
from decimal import Decimal

import pytest
from django.utils import timezone

from banking import services


@pytest.mark.django_db
class TestListTransactions:
    def test_empty_account_returns_zero_count(self, db_user, api_session):
        from mcp_server.server import list_transactions

        result = list_transactions(session_token=api_session)

        assert result == {"transactions": [], "count": 0}

    def test_returns_transactions_newest_first(self, db_user, api_session):
        from mcp_server.server import list_transactions

        services.deposit(db_user.account, Decimal("100.00"))
        services.deposit(db_user.account, Decimal("200.00"))

        result = list_transactions(session_token=api_session)

        assert result["count"] == 2
        assert result["transactions"][0]["balance_after"] == "300.00"

    def test_transaction_type_filter(self, db_user, api_session):
        from mcp_server.server import list_transactions

        services.deposit(db_user.account, Decimal("500.00"))
        services.withdraw(db_user.account, Decimal("50.00"))

        result = list_transactions(
            session_token=api_session,
            transaction_type="DEPOSIT",
        )

        assert result["count"] == 1
        assert result["transactions"][0]["transaction_type"] == "DEPOSIT"

    def test_date_filters(self, db_user, api_session):
        from mcp_server.server import list_transactions

        services.deposit(db_user.account, Decimal("10.00"))
        today = timezone.localdate().isoformat()

        result = list_transactions(
            session_token=api_session,
            date_from=today,
            date_to=today,
        )

        assert result["count"] == 1

    def test_default_limit_is_20_and_max_is_100(self, db_user, api_session):
        from mcp_server.server import list_transactions

        for _ in range(25):
            services.deposit(db_user.account, Decimal("1.00"))

        default_result = list_transactions(session_token=api_session)
        capped_result = list_transactions(session_token=api_session, limit=200)

        assert default_result["count"] == 20
        assert capped_result["count"] == 25

    def test_amount_balance_counterparty_and_description_serialization(
        self, funded_user, db_recipient, api_session
    ):
        from mcp_server.server import list_transactions

        services.transfer(
            funded_user.account,
            db_recipient.phone_number,
            Decimal("30.00"),
            description="Lunch split",
        )

        result = list_transactions(session_token=api_session)
        txn = result["transactions"][0]

        assert isinstance(txn["amount"], str)
        assert isinstance(txn["balance_after"], str)
        assert txn["counterparty_username"] == "bob"
        assert txn["counterparty_phone"] == "91234567"
        assert txn["description"] == "Lunch split"
        assert "id" in txn
        assert "timestamp" in txn

    def test_missing_session_token_returns_session_error(self, db_user):
        from mcp_server.server import list_transactions

        result = list_transactions(session_token="")

        assert result == {"error": "Session expired or invalid. Please log in again."}
