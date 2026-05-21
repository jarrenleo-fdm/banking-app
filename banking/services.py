"""Atomic banking service layer."""
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db import transaction

from .models import Account, Transaction


class BankingError(Exception):
    """Base exception for banking domain errors."""


class InvalidAmountError(BankingError):
    """Raised when a money amount is not positive."""


class InsufficientFundsError(BankingError):
    """Raised when an account cannot cover a debit."""


class RecipientNotFoundError(BankingError):
    """Raised when a transfer recipient cannot be found."""


class SelfTransferError(BankingError):
    """Raised when a user tries to transfer to their own account."""


def _validate_amount(amount):
    if amount <= Decimal("0.00"):
        raise InvalidAmountError("Amount must be greater than zero.")


@transaction.atomic
def deposit(account: Account, amount: Decimal) -> Transaction:
    _validate_amount(amount)
    account = Account.objects.get(pk=account.pk)
    account.balance += amount
    account.save(update_fields=["balance"])
    return Transaction.objects.create(
        account=account,
        transaction_type=Transaction.DEPOSIT,
        amount=amount,
        balance_after=account.balance,
    )


@transaction.atomic
def withdraw(account: Account, amount: Decimal) -> Transaction:
    _validate_amount(amount)
    account = Account.objects.get(pk=account.pk)
    if account.balance < amount:
        raise InsufficientFundsError("Insufficient funds")

    account.balance -= amount
    account.save(update_fields=["balance"])
    return Transaction.objects.create(
        account=account,
        transaction_type=Transaction.WITHDRAWAL,
        amount=amount,
        balance_after=account.balance,
    )


@transaction.atomic
def transfer(
    sender_account: Account, recipient_phone: str, amount: Decimal
) -> tuple[Transaction, Transaction]:
    _validate_amount(amount)
    recipient_phone = recipient_phone.strip().replace(" ", "").replace("-", "")
    user_model = get_user_model()

    sender_account = Account.objects.get(pk=sender_account.pk)
    try:
        recipient_account = Account.objects.select_related("user").get(
            user__phone_number=recipient_phone
        )
    except Account.DoesNotExist as exc:
        if not user_model.objects.filter(phone_number=recipient_phone).exists():
            raise RecipientNotFoundError(
                "No account found with that phone number"
            ) from exc
        raise

    if sender_account.pk == recipient_account.pk:
        raise SelfTransferError("Cannot transfer to your own account")

    if sender_account.balance < amount:
        raise InsufficientFundsError("Insufficient funds")

    sender_account.balance -= amount
    recipient_account.balance += amount
    sender_account.save(update_fields=["balance"])
    recipient_account.save(update_fields=["balance"])

    out_transaction = Transaction.objects.create(
        account=sender_account,
        transaction_type=Transaction.TRANSFER_OUT,
        amount=amount,
        balance_after=sender_account.balance,
        counterparty=recipient_account,
    )
    in_transaction = Transaction.objects.create(
        account=recipient_account,
        transaction_type=Transaction.TRANSFER_IN,
        amount=amount,
        balance_after=recipient_account.balance,
        counterparty=sender_account,
    )
    return out_transaction, in_transaction
