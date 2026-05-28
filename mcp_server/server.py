"""FastMCP server exposing personal banking tools only."""
import re
from decimal import Decimal

from asgiref.sync import sync_to_async
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import IntegrityError, transaction
from mcp.server.fastmcp import FastMCP

from accounts.api_keys import APIKeyAuthenticationError, verify_key
from banking import services
from banking.models import Account, Biller

from .auth import MCP_SESSION_TIMEOUT_MINUTES, SessionExpiredError, token_store
from .utils import _mcp_validate_amount, _mcp_validate_initial_deposit

mcp = FastMCP("banking")
User = get_user_model()


def _banking_tool(func):
    tool_func = sync_to_async(func, thread_sensitive=False)
    tool_func.__name__ = func.__name__
    tool_func.__doc__ = func.__doc__
    mcp.tool()(tool_func)
    return func


_ERR_INSUFFICIENT_FUNDS = "Insufficient funds."
_ERR_SESSION = "Session expired or invalid. Please log in again."


def _auth_username(session_token: str):
    """Return (username, None) or (None, error dict) for a protected call."""
    try:
        return token_store.validate_token(session_token), None
    except SessionExpiredError:
        return None, {"error": _ERR_SESSION}


def _auth_account(session_token: str):
    """Return (Account, None) or (None, error dict) for the session owner."""
    username, err = _auth_username(session_token)
    if err:
        return None, err
    try:
        account = Account.objects.select_related("user").get(user__username=username)
    except Account.DoesNotExist:
        return None, {"error": "Account not found."}
    return account, None


def _serialize_transaction(txn) -> dict:
    counterparty = txn.counterparty
    return {
        "id": txn.pk,
        "transaction_type": txn.transaction_type,
        "amount": str(txn.amount),
        "balance_after": str(txn.balance_after),
        "counterparty_username": (
            counterparty.user.username if counterparty else None
        ),
        "counterparty_phone": (
            counterparty.user.phone_number if counterparty else None
        ),
        "description": txn.description,
        "timestamp": txn.timestamp.isoformat(),
    }


def _serialize_biller(biller: Biller) -> dict:
    return {
        "id": biller.pk,
        "category": biller.name,
        "category_display": biller.get_name_display(),
        "reference": biller.reference,
        "created_at": biller.created_at.isoformat(),
    }


def _format_validation_error(exc: ValidationError) -> str:
    messages = []
    for message in exc.messages:
        messages.append(str(message))
    return " ".join(messages)


def _normalize_phone(phone_number: str) -> str:
    return str(phone_number or "").strip().replace(" ", "").replace("-", "")


def _required_signup_error(
    clean_name: str,
    clean_username: str,
    clean_email: str,
    clean_phone: str,
) -> str | None:
    required_checks = [
        (not clean_name, "Name is required."),
        (not clean_username, "Username is required."),
        (not clean_email, "Email is required."),
    ]
    for failed, message in required_checks:
        if failed:
            return message

    try:
        validate_email(clean_email)
    except ValidationError:
        return "Enter a valid email address."
    if not re.fullmatch(r"^[89]\d{7}$", clean_phone):
        return "Enter a valid Singapore mobile number."
    return None


def _unique_signup_error(
    clean_username: str,
    clean_email: str,
    clean_phone: str,
) -> str | None:
    uniqueness_checks = [
        (
            User.objects.filter(username__iexact=clean_username).exists(),
            "Username is already taken.",
        ),
        (
            User.objects.filter(email=clean_email).exists(),
            "Email is already registered.",
        ),
        (
            User.objects.filter(phone_number=clean_phone).exists(),
            "Phone number is already registered.",
        ),
    ]
    for failed, message in uniqueness_checks:
        if failed:
            return message
    return None


def _password_signup_error(password: str) -> str | None:
    try:
        validate_password(password)
    except ValidationError as exc:
        return _format_validation_error(exc)
    return None


def _clean_signup_fields(
    name: str,
    username: str,
    email: str,
    phone_number: str,
) -> dict:
    return {
        "name": str(name or "").strip(),
        "username": str(username or "").strip(),
        "email": str(email or "").strip().lower(),
        "phone_number": _normalize_phone(phone_number),
    }


def _validate_signup_fields(
    name: str,
    username: str,
    email: str,
    phone_number: str,
    password: str,
) -> tuple[dict, dict | None]:
    clean_fields = _clean_signup_fields(name, username, email, phone_number)
    error = (
        _required_signup_error(
            clean_fields["name"],
            clean_fields["username"],
            clean_fields["email"],
            clean_fields["phone_number"],
        )
        or _unique_signup_error(
            clean_fields["username"],
            clean_fields["email"],
            clean_fields["phone_number"],
        )
        or _password_signup_error(password)
    )
    if error:
        return {}, {"error": error}

    clean_fields["password"] = password
    return clean_fields, None


@_banking_tool
def create_personal_account(
    name: str,
    username: str,
    email: str,
    phone_number: str,
    password: str,
    initial_deposit: str = "0.00",
) -> dict:
    """Create a personal account without creating or returning an API key."""
    try:
        starting_balance = _mcp_validate_initial_deposit(initial_deposit)
    except ValueError as exc:
        return {"error": str(exc)}

    clean_fields, err = _validate_signup_fields(
        name, username, email, phone_number, password
    )
    if err:
        return err

    try:
        with transaction.atomic():
            user = User.objects.create_user(**clean_fields)
            if starting_balance > Decimal("0.00"):
                services.deposit(user.account, starting_balance)
            user.account.refresh_from_db()
    except IntegrityError:
        return {"error": "Could not create account with the supplied details."}

    return {
        "username": user.username,
        "name": user.name,
        "phone_number": user.phone_number,
        "balance": str(user.account.balance),
        "created_at": user.account.created_at.isoformat(),
    }


@_banking_tool
def login_with_api_key(api_key: str) -> dict:
    """Issue a short-lived MCP session for a valid active API key."""
    try:
        user, key = verify_key(api_key)
    except APIKeyAuthenticationError:
        return {"error": "Authentication failed."}

    token = token_store.issue_token(
        user.username,
        api_key_identifier=key.identifier,
    )
    return {
        "session_token": token,
        "expires_in_minutes": MCP_SESSION_TIMEOUT_MINUTES,
        "username": user.username,
        "auth_method": "api_key",
        "api_key_identifier": key.identifier,
    }


@_banking_tool
def logout(session_token: str) -> dict:
    """Invalidate the current MCP session token."""
    revoked = token_store.revoke_token(session_token)
    if not revoked:
        return {"error": _ERR_SESSION}
    return {"message": "Logged out successfully."}


@_banking_tool
def get_account(session_token: str) -> dict:
    """Return the authenticated user's personal account summary."""
    account, err = _auth_account(session_token)
    if err:
        return err
    return {
        "username": account.user.username,
        "name": account.user.name,
        "phone_number": account.user.phone_number,
        "balance": str(account.balance),
        "created_at": account.created_at.isoformat(),
    }


@_banking_tool
def list_transactions(
    session_token: str,
    transaction_type: str = None,
    date_from: str = None,
    date_to: str = None,
    limit: int = 20,
) -> dict:
    """Return the authenticated user's personal transaction history."""
    account, err = _auth_account(session_token)
    if err:
        return err

    qs = account.transactions.select_related("counterparty__user")
    if transaction_type:
        qs = qs.filter(transaction_type=transaction_type)
    if date_from:
        qs = qs.filter(timestamp__date__gte=date_from)
    if date_to:
        qs = qs.filter(timestamp__date__lte=date_to)

    try:
        requested_limit = int(limit)
    except (TypeError, ValueError):
        requested_limit = 20
    requested_limit = min(max(requested_limit, 1), 100)
    rows = [_serialize_transaction(txn) for txn in qs[:requested_limit]]
    return {"transactions": rows, "count": len(rows)}


@_banking_tool
def list_billers(session_token: str) -> dict:
    """Return the authenticated user's saved billers."""
    account, err = _auth_account(session_token)
    if err:
        return err

    billers = [_serialize_biller(biller) for biller in account.billers.all()]
    return {"billers": billers, "count": len(billers)}


@_banking_tool
def deposit_funds(amount: str, session_token: str) -> dict:
    """Deposit funds into the authenticated user's personal account."""
    account, err = _auth_account(session_token)
    if err:
        return err
    try:
        amt = _mcp_validate_amount(amount)
        txn = services.deposit(account, amt)
    except ValueError as exc:
        return {"error": str(exc)}
    except services.BankingError as exc:
        return {"error": str(exc)}

    return {"new_balance": str(txn.balance_after), "transaction_id": txn.pk}


@_banking_tool
def withdraw_funds(amount: str, session_token: str) -> dict:
    """Withdraw funds from the authenticated user's personal account."""
    account, err = _auth_account(session_token)
    if err:
        return err
    try:
        amt = _mcp_validate_amount(amount)
        txn = services.withdraw(account, amt)
    except ValueError as exc:
        return {"error": str(exc)}
    except services.InsufficientFundsError:
        return {"error": _ERR_INSUFFICIENT_FUNDS}
    except services.BankingError as exc:
        return {"error": str(exc)}

    return {"new_balance": str(txn.balance_after), "transaction_id": txn.pk}


@_banking_tool
def transfer_funds(
    recipient_phone: str,
    amount: str,
    session_token: str,
    description: str = "",
) -> dict:
    """Transfer funds to a recipient identified by phone number."""
    account, err = _auth_account(session_token)
    if err:
        return err
    clean_description = description or ""
    if len(clean_description) > 200:
        return {"error": "Description must be 200 characters or fewer."}

    try:
        amt = _mcp_validate_amount(amount)
        out_txn, in_txn = services.transfer(
            account,
            recipient_phone,
            amt,
            clean_description,
        )
    except (
        ValueError,
        services.RecipientNotFoundError,
        services.SelfTransferError,
        services.InsufficientFundsError,
        services.BankingError,
    ) as exc:
        return {"error": _transfer_error_message(exc)}

    return {
        "sender_new_balance": str(out_txn.balance_after),
        "out_transaction_id": out_txn.pk,
        "in_transaction_id": in_txn.pk,
    }


def _transfer_error_message(exc: Exception) -> str:
    if isinstance(exc, services.RecipientNotFoundError):
        return "Recipient not found."
    if isinstance(exc, services.SelfTransferError):
        return "Cannot transfer to your own account."
    if isinstance(exc, services.InsufficientFundsError):
        return _ERR_INSUFFICIENT_FUNDS
    return str(exc)


@_banking_tool
def add_biller(session_token: str, category: str, reference: str) -> dict:
    """Add a saved biller to the authenticated user's personal account."""
    account, err = _auth_account(session_token)
    if err:
        return err

    valid_categories = [choice[0] for choice in Biller.BILLER_CATEGORIES]
    if category not in valid_categories:
        return {
            "error": (
                "Invalid category. Must be one of: "
                f"{', '.join(valid_categories)}."
            )
        }

    clean_reference = str(reference or "").strip()
    if not clean_reference:
        return {"error": "Reference is required."}

    duplicate = Biller.objects.filter(
        account=account,
        name=category,
        reference=clean_reference,
    ).exists()
    if duplicate:
        return {
            "error": "A biller with this category and reference already exists."
        }

    try:
        with transaction.atomic():
            biller = Biller.objects.create(
                account=account,
                name=category,
                reference=clean_reference,
            )
    except IntegrityError:
        return {
            "error": "A biller with this category and reference already exists."
        }

    return _serialize_biller(biller)


@_banking_tool
def pay_bill(biller_id: int, amount: str, session_token: str) -> dict:
    """Pay one of the authenticated user's saved billers."""
    account, err = _auth_account(session_token)
    if err:
        return err

    try:
        biller = account.billers.get(pk=biller_id)
    except Biller.DoesNotExist:
        return {"error": "Biller not found."}

    try:
        amt = _mcp_validate_amount(amount)
        txn = services.pay_bill(account, biller, amt)
    except ValueError as exc:
        return {"error": str(exc)}
    except services.InsufficientFundsError:
        return {"error": _ERR_INSUFFICIENT_FUNDS}
    except services.BankingError as exc:
        return {"error": str(exc)}

    return {"new_balance": str(txn.balance_after), "transaction_id": txn.pk}
