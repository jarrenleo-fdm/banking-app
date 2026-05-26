"""Tests for list_pending_transactions, approve_transaction, reject_transaction (US6)."""
from decimal import Decimal

import pytest

from banking import services
from banking.models import PendingTransaction


def _issue_token(username):
    from mcp_server.auth import token_store
    return token_store.issue_token(username)


def _make_pending(business_account, amount="1000.00"):
    return PendingTransaction.objects.create(
        business_account=business_account,
        transaction_type=PendingTransaction.WITHDRAWAL,
        amount=amount,
        status=PendingTransaction.PENDING,
    )


@pytest.mark.django_db
class TestListPendingTransactions:
    def test_returns_pending_transactions(self, db_business):
        from mcp_server.server import list_pending_transactions

        pt = _make_pending(db_business)
        result = list_pending_transactions(identifier="202312345A")
        assert result["count"] == 1
        row = result["pending_transactions"][0]
        assert row["id"] == pt.pk
        assert row["transaction_type"] == "WITHDRAWAL"
        assert row["amount"] == "1000.00"
        assert "created_at" in row

    def test_excludes_non_pending(self, db_business):
        from mcp_server.server import list_pending_transactions

        pt = _make_pending(db_business)
        pt.status = PendingTransaction.APPROVED
        pt.save()
        result = list_pending_transactions(identifier="202312345A")
        assert result["count"] == 0

    def test_empty_returns_zero_count(self, db_business):
        from mcp_server.server import list_pending_transactions

        result = list_pending_transactions(identifier="Acme Pte Ltd")
        assert result == {"pending_transactions": [], "count": 0}

    def test_unknown_identifier_returns_error(self):
        from mcp_server.server import list_pending_transactions

        result = list_pending_transactions(identifier="UNKNOWN")
        assert "error" in result

    def test_no_session_token_required(self, db_business):
        from mcp_server.server import list_pending_transactions

        result = list_pending_transactions(identifier="202312345A")
        assert "error" not in result


@pytest.mark.django_db
class TestApproveTransaction:
    def test_approve_updates_status_and_balance(self, db_business):
        from mcp_server.server import approve_transaction

        services.deposit_to_business(db_business, Decimal("5000.00"))
        pt = _make_pending(db_business, "1000.00")
        token = _issue_token("authoriser.acme")
        result = approve_transaction(
            pending_transaction_id=pt.pk, session_token=token
        )
        assert result["status"] == "APPROVED"
        assert result["business_new_balance"] == "54000.00"

    def test_non_pending_returns_error(self, db_business):
        from mcp_server.server import approve_transaction

        pt = _make_pending(db_business)
        pt.status = PendingTransaction.REJECTED
        pt.save()
        token = _issue_token("authoriser.acme")
        result = approve_transaction(pt.pk, token)
        assert result == {"error": "Transaction is no longer pending."}

    def test_non_authoriser_returns_not_authorised(self, db_business, db_user):
        from mcp_server.server import approve_transaction

        pt = _make_pending(db_business)
        token = _issue_token("alice")
        result = approve_transaction(pt.pk, token)
        assert result == {"error": "Not authorised to perform this action."}

    def test_expired_token_returns_session_error(self, db_business):
        from mcp_server.server import approve_transaction

        pt = _make_pending(db_business)
        result = approve_transaction(pt.pk, "e" * 64)
        assert result == {"error": "Session expired or invalid. Please log in again."}


@pytest.mark.django_db
class TestRejectTransaction:
    def test_reject_returns_rejected_status(self, db_business):
        from mcp_server.server import reject_transaction

        pt = _make_pending(db_business)
        token = _issue_token("authoriser.acme")
        result = reject_transaction(
            pending_transaction_id=pt.pk, session_token=token
        )
        assert result == {"status": "REJECTED"}

    def test_balance_unchanged_after_reject(self, db_business):
        from mcp_server.server import reject_transaction

        services.deposit_to_business(db_business, Decimal("5000.00"))
        pt = _make_pending(db_business, "1000.00")
        token = _issue_token("authoriser.acme")
        reject_transaction(pt.pk, token)
        db_business.refresh_from_db()
        assert db_business.balance == Decimal("55000.00")

    def test_non_pending_returns_error(self, db_business):
        from mcp_server.server import reject_transaction

        pt = _make_pending(db_business)
        pt.status = PendingTransaction.APPROVED
        pt.save()
        token = _issue_token("authoriser.acme")
        result = reject_transaction(pt.pk, token)
        assert result == {"error": "Transaction is no longer pending."}

    def test_non_authoriser_returns_not_authorised(self, db_business, db_user):
        from mcp_server.server import reject_transaction

        pt = _make_pending(db_business)
        token = _issue_token("alice")
        result = reject_transaction(pt.pk, token)
        assert result == {"error": "Not authorised to perform this action."}

    def test_expired_token_returns_session_error(self, db_business):
        from mcp_server.server import reject_transaction

        pt = _make_pending(db_business)
        result = reject_transaction(pt.pk, "f" * 64)
        assert result == {"error": "Session expired or invalid. Please log in again."}
