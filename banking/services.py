"""Atomic banking service layer."""
import random
import re
import string
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone

from .models import Account, AccountManagerProfile, Authoriser, Biller, BusinessAccount, BusinessTransaction, PendingTransaction, Transaction


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
def pay_bill(account: Account, biller: Biller, amount: Decimal) -> Transaction:
    _validate_amount(amount)
    account = Account.objects.get(pk=account.pk)
    if account.balance < amount:
        raise InsufficientFundsError("Insufficient funds")

    account.balance -= amount
    account.save(update_fields=["balance"])
    return Transaction.objects.create(
        account=account,
        transaction_type=Transaction.BILL_PAYMENT,
        amount=amount,
        balance_after=account.balance,
        description=f"{biller.get_name_display()} ({biller.reference})",
    )



@transaction.atomic
def transfer(
    sender_account: Account,
    recipient_phone: str,
    amount: Decimal,
    description: str = "",
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
        description=description,
    )
    in_transaction = Transaction.objects.create(
        account=recipient_account,
        transaction_type=Transaction.TRANSFER_IN,
        amount=amount,
        balance_after=recipient_account.balance,
        counterparty=sender_account,
        description=description,
    )
    return out_transaction, in_transaction


def _next_odd_phone():
    """Return the next available odd phone number ≥ 80000001 for managers."""
    User = get_user_model()
    existing = set(User.objects.values_list("phone_number", flat=True))
    candidate = 80000001
    while str(candidate) in existing:
        candidate += 2
    return str(candidate)


def _next_even_phone():
    """Return the next available even phone number ≥ 80000002 for authorisers."""
    User = get_user_model()
    existing = set(User.objects.values_list("phone_number", flat=True))
    candidate = 80000002
    while str(candidate) in existing:
        candidate += 2
    return str(candidate)


def _make_slug(company_name: str) -> str:
    slug = re.sub(r"[^a-z0-9]", "", company_name.lower())
    return slug[:20]


def _unique_username(prefix: str) -> str:
    User = get_user_model()
    base = f"{prefix}"
    if not User.objects.filter(username=base).exists():
        return base
    i = 2
    while User.objects.filter(username=f"{base}{i}").exists():
        i += 1
    return f"{base}{i}"


def _random_password() -> str:
    chars = string.ascii_letters + string.digits
    return "Demo@" + "".join(random.choices(chars, k=6))


@transaction.atomic
def create_business_account_mock(
    company_name: str,
    uen: str,
    street: str,
    city: str,
    postal_code: str,
    initial_deposit: Decimal,
) -> dict:
    """
    Mock SQL: creates a BusinessAccount, manager user, and authoriser user atomically.
    Returns a credentials dict shown once on the confirmation screen.
    """
    if initial_deposit < Decimal("7000.00"):
        raise BankingError("Initial deposit must be at least 7,000.")
    User = get_user_model()
    slug = _make_slug(company_name)

    business_account = BusinessAccount.objects.create(
        company_name=company_name,
        uen=uen,
        street=street,
        city=city,
        postal_code=postal_code,
        balance=initial_deposit,
    )
    BusinessTransaction.objects.create(
        business_account=business_account,
        transaction_type=BusinessTransaction.DEPOSIT,
        amount=initial_deposit,
        balance_after=initial_deposit,
    )

    manager_phone = _next_odd_phone()
    manager_username = _unique_username(f"manager.{slug}")
    manager_password = _random_password()
    manager_user = User.objects.create_user(
        username=manager_username,
        email=f"{manager_username}@demo.internal",
        name=f"Manager ({company_name})",
        phone_number=manager_phone,
        password=manager_password,
    )
    AccountManagerProfile.objects.create(user=manager_user, business_account=business_account)

    authoriser_phone = _next_even_phone()
    authoriser_username = _unique_username(f"authoriser.{slug}")
    authoriser_password = _random_password()
    authoriser_user = User.objects.create_user(
        username=authoriser_username,
        email=f"{authoriser_username}@demo.internal",
        name=f"Authoriser ({company_name})",
        phone_number=authoriser_phone,
        password=authoriser_password,
    )
    Authoriser.objects.create(user=authoriser_user, business_account=business_account)

    return {
        "business_account_id": business_account.pk,
        "manager_username": manager_username,
        "manager_password": manager_password,
        "manager_phone": manager_phone,
        "authoriser_username": authoriser_username,
        "authoriser_password": authoriser_password,
        "authoriser_phone": authoriser_phone,
    }


@transaction.atomic
def deposit_to_business(business_account: BusinessAccount, amount: Decimal) -> BusinessTransaction:
    _validate_amount(amount)
    ba = BusinessAccount.objects.select_for_update().get(pk=business_account.pk)
    ba.balance += amount
    ba.save(update_fields=["balance"])
    return BusinessTransaction.objects.create(
        business_account=ba,
        transaction_type=BusinessTransaction.DEPOSIT,
        amount=amount,
        balance_after=ba.balance,
    )


@transaction.atomic
def create_pending_withdrawal(business_account: BusinessAccount, amount: Decimal) -> PendingTransaction:
    _validate_amount(amount)
    ba = BusinessAccount.objects.get(pk=business_account.pk)
    if ba.balance - amount < Decimal("7000.00"):
        raise InsufficientFundsError("Transaction would bring balance below minimum (7,000).")
    return PendingTransaction.objects.create(
        business_account=ba,
        transaction_type=PendingTransaction.WITHDRAWAL,
        amount=amount,
    )


@transaction.atomic
def create_pending_transfer(business_account: BusinessAccount, amount: Decimal, recipient_phone: str) -> PendingTransaction:
    _validate_amount(amount)
    ba = BusinessAccount.objects.get(pk=business_account.pk)
    if ba.balance - amount < Decimal("7000.00"):
        raise InsufficientFundsError("Transaction would bring balance below minimum (7,000).")
    try:
        recipient_account = Account.objects.get(user__phone_number=recipient_phone)
    except Account.DoesNotExist as exc:
        raise RecipientNotFoundError("No account found with that phone number.") from exc
    return PendingTransaction.objects.create(
        business_account=ba,
        transaction_type=PendingTransaction.TRANSFER_OUT,
        amount=amount,
        counterparty=recipient_account,
    )


@transaction.atomic
def create_pending_bill_payment(business_account: BusinessAccount, amount: Decimal, category: str, reference: str) -> PendingTransaction:
    _validate_amount(amount)
    ba = BusinessAccount.objects.get(pk=business_account.pk)
    if ba.balance - amount < Decimal("7000.00"):
        raise InsufficientFundsError("Transaction would bring balance below minimum (7,000).")
    return PendingTransaction.objects.create(
        business_account=ba,
        transaction_type=PendingTransaction.BILL_PAYMENT,
        amount=amount,
        description=f"{category} ({reference})",
    )


@transaction.atomic
def withdraw_from_business(business_account: BusinessAccount, amount: Decimal) -> BusinessTransaction:
    _validate_amount(amount)
    ba = BusinessAccount.objects.select_for_update().get(pk=business_account.pk)
    if ba.balance - amount < Decimal("7000.00"):
        raise InsufficientFundsError("Transaction would bring balance below minimum (7,000).")
    ba.balance -= amount
    ba.save(update_fields=["balance"])
    return BusinessTransaction.objects.create(
        business_account=ba,
        transaction_type=BusinessTransaction.WITHDRAWAL,
        amount=amount,
        balance_after=ba.balance,
    )


@transaction.atomic
def transfer_from_business(business_account: BusinessAccount, amount: Decimal, recipient_phone: str) -> BusinessTransaction:
    _validate_amount(amount)
    ba = BusinessAccount.objects.select_for_update().get(pk=business_account.pk)
    if ba.balance - amount < Decimal("7000.00"):
        raise InsufficientFundsError("Transaction would bring balance below minimum (7,000).")
    try:
        recipient_account = Account.objects.get(user__phone_number=recipient_phone)
    except Account.DoesNotExist as exc:
        raise RecipientNotFoundError("No account found with that phone number.") from exc
    ba.balance -= amount
    recipient_account.balance += amount
    ba.save(update_fields=["balance"])
    recipient_account.save(update_fields=["balance"])
    Transaction.objects.create(
        account=recipient_account,
        transaction_type=Transaction.TRANSFER_IN,
        amount=amount,
        balance_after=recipient_account.balance,
    )
    return BusinessTransaction.objects.create(
        business_account=ba,
        transaction_type=BusinessTransaction.TRANSFER_OUT,
        amount=amount,
        balance_after=ba.balance,
        counterparty=recipient_account,
    )


@transaction.atomic
def pay_bill_from_business(business_account: BusinessAccount, amount: Decimal, category: str, reference: str) -> BusinessTransaction:
    _validate_amount(amount)
    ba = BusinessAccount.objects.select_for_update().get(pk=business_account.pk)
    if ba.balance - amount < Decimal("7000.00"):
        raise InsufficientFundsError("Transaction would bring balance below minimum (7,000).")
    ba.balance -= amount
    ba.save(update_fields=["balance"])
    return BusinessTransaction.objects.create(
        business_account=ba,
        transaction_type=BusinessTransaction.BILL_PAYMENT,
        amount=amount,
        balance_after=ba.balance,
        description=f"{category} ({reference})",
    )


@transaction.atomic
def approve_business_pending(pending_tx: PendingTransaction, decided_by) -> bool:
    pt = PendingTransaction.objects.select_for_update().get(pk=pending_tx.pk)
    ba = BusinessAccount.objects.select_for_update().get(pk=pt.business_account_id)
    if ba.balance - pt.amount < Decimal("7000.00"):
        reject_business_pending(pending_tx, decided_by)
        return False
    ba.balance -= pt.amount
    ba.save(update_fields=["balance"])
    pt.status = PendingTransaction.APPROVED
    pt.decided_at = timezone.now()
    pt.decided_by = decided_by
    pt.save(update_fields=["status", "decided_at", "decided_by"])
    BusinessTransaction.objects.create(
        business_account=ba,
        transaction_type=pt.transaction_type,
        amount=pt.amount,
        balance_after=ba.balance,
        counterparty=pt.counterparty,
        description=pt.description,
    )
    return True


@transaction.atomic
def reject_business_pending(pending_tx: PendingTransaction, decided_by) -> None:
    pt = PendingTransaction.objects.get(pk=pending_tx.pk)
    ba = pt.business_account
    pt.status = PendingTransaction.REJECTED
    pt.decided_at = timezone.now()
    pt.decided_by = decided_by
    pt.save(update_fields=["status", "decided_at", "decided_by"])
    BusinessTransaction.objects.create(
        business_account=ba,
        transaction_type=BusinessTransaction.REJECTED,
        amount=pt.amount,
        balance_after=ba.balance,
        description=f"Rejected: {pt.get_transaction_type_display()}",
    )
