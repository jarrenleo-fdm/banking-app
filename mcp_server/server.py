"""FastMCP server with all 13 banking tools."""
from asgiref.sync import sync_to_async
from django.contrib.auth import authenticate, get_user_model
from django.db.models import Q
from mcp.server.fastmcp import FastMCP

from banking import services
from banking.models import (
    Account,
    BusinessAccount,
    Biller,
    PendingTransaction,
)

from .auth import MCP_SESSION_TIMEOUT_MINUTES, SessionExpiredError, token_store
from .utils import _mcp_validate_amount

mcp = FastMCP("banking")
User = get_user_model()


def _banking_tool(func):
    return mcp.tool()(sync_to_async(func, thread_sensitive=False))

_ERR_NOT_AUTHORISED = "Not authorised to perform this action."
_ERR_INSUFFICIENT_FUNDS = "Insufficient funds."


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _get_account(username: str):
    """Return Account or error dict."""
    try:
        return Account.objects.select_related("user").get(user__username=username)
    except Account.DoesNotExist:
        return {"error": f"Account not found for user '{username}'."}


def _get_business(identifier: str):
    """Return BusinessAccount matched by UEN or company name, or error dict."""
    ba = BusinessAccount.objects.filter(
        Q(uen__iexact=identifier) | Q(company_name__iexact=identifier)
    ).first()
    if ba is None:
        return {"error": f"Business account not found: '{identifier}'."}
    return ba


def _auth(session_token: str):
    """Validate token; return (username, None) or (None, error_dict)."""
    try:
        return token_store.validate_token(session_token), None
    except SessionExpiredError as exc:
        return None, {"error": str(exc)}


# ---------------------------------------------------------------------------
# Read tools (no session_token required)
# ---------------------------------------------------------------------------


@_banking_tool
def get_account(username: str) -> dict:
    result = _get_account(username)
    if isinstance(result, dict):
        return result
    acct = result
    return {
        "username": acct.user.username,
        "name": acct.user.name,
        "balance": str(acct.balance),
        "created_at": acct.created_at.isoformat(),
    }


@_banking_tool
def get_business_account(identifier: str) -> dict:
    result = _get_business(identifier)
    if isinstance(result, dict):
        return result
    ba = BusinessAccount.objects.select_related(
        "manager__user", "authoriser__user"
    ).get(pk=result.pk)
    return {
        "company_name": ba.company_name,
        "uen": ba.uen,
        "address": f"{ba.street}, {ba.city} {ba.postal_code}",
        "balance": str(ba.balance),
        "manager": {
            "username": ba.manager.user.username,
            "name": ba.manager.user.name,
        },
        "authoriser": {
            "username": ba.authoriser.user.username,
            "name": ba.authoriser.user.name,
        },
        "created_at": ba.created_at.isoformat(),
    }


@_banking_tool
def list_transactions(
    username: str,
    transaction_type: str = None,
    date_from: str = None,
    date_to: str = None,
    limit: int = 20,
) -> dict:
    result = _get_account(username)
    if isinstance(result, dict):
        return result
    qs = result.transactions.select_related("counterparty__user")
    if transaction_type:
        qs = qs.filter(transaction_type=transaction_type)
    if date_from:
        qs = qs.filter(timestamp__date__gte=date_from)
    if date_to:
        qs = qs.filter(timestamp__date__lte=date_to)
    limit = min(max(limit, 1), 100)
    rows = []
    for txn in qs[:limit]:
        rows.append(
            {
                "id": txn.pk,
                "transaction_type": txn.transaction_type,
                "amount": str(txn.amount),
                "balance_after": str(txn.balance_after),
                "counterparty_username": (
                    txn.counterparty.user.username if txn.counterparty else None
                ),
                "description": txn.description,
                "timestamp": txn.timestamp.isoformat(),
            }
        )
    return {"transactions": rows, "count": len(rows)}


@_banking_tool
def list_business_transactions(
    identifier: str,
    transaction_type: str = None,
    date_from: str = None,
    date_to: str = None,
    limit: int = 20,
) -> dict:
    result = _get_business(identifier)
    if isinstance(result, dict):
        return result
    qs = result.transactions.all()
    if transaction_type:
        qs = qs.filter(transaction_type=transaction_type)
    if date_from:
        qs = qs.filter(timestamp__date__gte=date_from)
    if date_to:
        qs = qs.filter(timestamp__date__lte=date_to)
    limit = min(max(limit, 1), 100)
    rows = []
    for txn in qs[:limit]:
        rows.append(
            {
                "id": txn.pk,
                "transaction_type": txn.transaction_type,
                "amount": str(txn.amount),
                "balance_after": str(txn.balance_after),
                "description": txn.description,
                "timestamp": txn.timestamp.isoformat(),
            }
        )
    return {"transactions": rows, "count": len(rows)}


@_banking_tool
def list_billers(username: str) -> dict:
    result = _get_account(username)
    if isinstance(result, dict):
        return result
    billers = []
    for b in result.billers.all():
        billers.append(
            {
                "id": b.pk,
                "category": b.name,
                "category_display": b.get_name_display(),
                "reference": b.reference,
                "created_at": b.created_at.isoformat(),
            }
        )
    return {"billers": billers, "count": len(billers)}


@_banking_tool
def list_pending_transactions(identifier: str) -> dict:
    result = _get_business(identifier)
    if isinstance(result, dict):
        return result
    qs = result.pending_transactions.filter(
        status=PendingTransaction.PENDING
    ).select_related("counterparty__user")
    rows = []
    for pt in qs:
        rows.append(
            {
                "id": pt.pk,
                "transaction_type": pt.transaction_type,
                "amount": str(pt.amount),
                "counterparty_username": (
                    pt.counterparty.user.username if pt.counterparty else None
                ),
                "description": pt.description,
                "created_at": pt.created_at.isoformat(),
            }
        )
    return {"pending_transactions": rows, "count": len(rows)}


# ---------------------------------------------------------------------------
# Auth tool
# ---------------------------------------------------------------------------


@_banking_tool
def login(username: str, password: str) -> dict:
    user = authenticate(username=username, password=password)
    if user is None:
        return {"error": "Authentication failed."}
    token = token_store.issue_token(username)
    return {"session_token": token, "expires_in_minutes": MCP_SESSION_TIMEOUT_MINUTES}


# ---------------------------------------------------------------------------
# Write tools (session_token required)
# ---------------------------------------------------------------------------


@_banking_tool
def deposit_funds(username: str, amount: str, session_token: str) -> dict:
    try:
        amt = _mcp_validate_amount(amount)
    except ValueError as exc:
        return {"error": str(exc)}
    owner, err = _auth(session_token)
    if err:
        return err
    if owner != username:
        return {"error": _ERR_NOT_AUTHORISED}
    result = _get_account(username)
    if isinstance(result, dict):
        return result
    try:
        txn = services.deposit(result, amt)
    except services.BankingError as exc:
        return {"error": str(exc)}
    return {"new_balance": str(txn.balance_after), "transaction_id": txn.pk}


@_banking_tool
def withdraw_funds(username: str, amount: str, session_token: str) -> dict:
    try:
        amt = _mcp_validate_amount(amount)
    except ValueError as exc:
        return {"error": str(exc)}
    owner, err = _auth(session_token)
    if err:
        return err
    if owner != username:
        return {"error": _ERR_NOT_AUTHORISED}
    result = _get_account(username)
    if isinstance(result, dict):
        return result
    try:
        txn = services.withdraw(result, amt)
    except services.InsufficientFundsError:
        return {"error": _ERR_INSUFFICIENT_FUNDS}
    except services.BankingError as exc:
        return {"error": str(exc)}
    return {"new_balance": str(txn.balance_after), "transaction_id": txn.pk}


@_banking_tool
def transfer_funds(
    from_username: str,
    to_username: str,
    amount: str,
    session_token: str,
    description: str = "",
) -> dict:
    try:
        amt = _mcp_validate_amount(amount)
    except ValueError as exc:
        return {"error": str(exc)}
    owner, err = _auth(session_token)
    if err:
        return err
    if owner != from_username:
        return {"error": _ERR_NOT_AUTHORISED}
    sender = _get_account(from_username)
    if isinstance(sender, dict):
        return sender
    try:
        recipient_user = User.objects.get(username=to_username)
    except User.DoesNotExist:
        return {"error": f"Recipient '{to_username}' not found."}
    try:
        out_txn, _in_txn = services.transfer(
            sender, recipient_user.phone_number, amt, description
        )
    except services.RecipientNotFoundError:
        return {"error": f"Recipient '{to_username}' not found."}
    except services.SelfTransferError:
        return {"error": "Cannot transfer to your own account."}
    except services.InsufficientFundsError:
        return {"error": _ERR_INSUFFICIENT_FUNDS}
    except services.BankingError as exc:
        return {"error": str(exc)}
    return {
        "sender_new_balance": str(out_txn.balance_after),
        "out_transaction_id": out_txn.pk,
        "in_transaction_id": _in_txn.pk,
    }


@_banking_tool
def pay_bill(username: str, biller_id: int, amount: str, session_token: str) -> dict:
    try:
        amt = _mcp_validate_amount(amount)
    except ValueError as exc:
        return {"error": str(exc)}
    owner, err = _auth(session_token)
    if err:
        return err
    if owner != username:
        return {"error": _ERR_NOT_AUTHORISED}
    result = _get_account(username)
    if isinstance(result, dict):
        return result
    try:
        biller = result.billers.get(pk=biller_id)
    except Biller.DoesNotExist:
        return {"error": "Biller not found."}
    try:
        txn = services.pay_bill(result, biller, amt)
    except services.InsufficientFundsError:
        return {"error": _ERR_INSUFFICIENT_FUNDS}
    except services.BankingError as exc:
        return {"error": str(exc)}
    return {"new_balance": str(txn.balance_after), "transaction_id": txn.pk}


@_banking_tool
def approve_transaction(pending_transaction_id: int, session_token: str) -> dict:
    owner, err = _auth(session_token)
    if err:
        return err
    try:
        pt = PendingTransaction.objects.select_related(
            "business_account__authoriser__user"
        ).get(pk=pending_transaction_id)
    except PendingTransaction.DoesNotExist:
        return {"error": "Transaction not found."}
    if pt.status != PendingTransaction.PENDING:
        return {"error": "Transaction is no longer pending."}
    try:
        authoriser = pt.business_account.authoriser
    except Exception:
        return {"error": _ERR_NOT_AUTHORISED}
    if authoriser.user.username != owner:
        return {"error": _ERR_NOT_AUTHORISED}
    decided_by = User.objects.get(username=owner)
    result = services.approve_business_pending(pt, decided_by)
    if not result:
        return {"status": "AUTO_REJECTED", "reason": "minimum balance breach"}
    ba = BusinessAccount.objects.get(pk=pt.business_account_id)
    return {"status": "APPROVED", "business_new_balance": str(ba.balance)}


@_banking_tool
def reject_transaction(
    pending_transaction_id: int, session_token: str, reason: str = ""
) -> dict:
    owner, err = _auth(session_token)
    if err:
        return err
    try:
        pt = PendingTransaction.objects.select_related(
            "business_account__authoriser__user"
        ).get(pk=pending_transaction_id)
    except PendingTransaction.DoesNotExist:
        return {"error": "Transaction not found."}
    if pt.status != PendingTransaction.PENDING:
        return {"error": "Transaction is no longer pending."}
    try:
        authoriser = pt.business_account.authoriser
    except Exception:
        return {"error": _ERR_NOT_AUTHORISED}
    if authoriser.user.username != owner:
        return {"error": _ERR_NOT_AUTHORISED}
    try:
        decided_by = User.objects.get(username=owner)
        services.reject_business_pending(pt, decided_by)
    except services.BankingError as exc:
        return {"error": str(exc)}
    return {"status": "REJECTED"}
