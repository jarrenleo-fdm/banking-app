"""Integration tests for atomic banking services."""
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model

from banking.models import Transaction
from banking.services import (
    InsufficientFundsError,
    InvalidAmountError,
    RecipientNotFoundError,
    SelfTransferError,
    deposit,
    transfer,
    withdraw,
)


User = get_user_model()


def create_user(username, phone_number, email=None):
    return User.objects.create_user(
        username=username,
        email=email or f"{username.lower()}@example.com",
        name=f"{username} Example",
        phone_number=phone_number,
        password="StrongerPass123",
    )


def test_deposit_positive_amount_increases_balance_and_records_transaction():
    user = create_user("Alice", "81234567")

    transaction = deposit(user.account, Decimal("100.00"))
    user.account.refresh_from_db()

    assert user.account.balance == Decimal("100.00")
    assert transaction.transaction_type == Transaction.DEPOSIT
    assert transaction.amount == Decimal("100.00")
    assert transaction.balance_after == Decimal("100.00")


@pytest.mark.parametrize("amount", [Decimal("0.00"), Decimal("-1.00")])
def test_deposit_rejects_non_positive_amount(amount):
    user = create_user("Alice", "81234567")

    with pytest.raises(InvalidAmountError):
        deposit(user.account, amount)

    user.account.refresh_from_db()
    assert user.account.balance == Decimal("0.00")
    assert Transaction.objects.count() == 0


def test_withdraw_positive_amount_decreases_balance_and_records_transaction():
    user = create_user("Alice", "81234567")
    deposit(user.account, Decimal("100.00"))

    transaction = withdraw(user.account, Decimal("30.00"))
    user.account.refresh_from_db()

    assert user.account.balance == Decimal("70.00")
    assert transaction.transaction_type == Transaction.WITHDRAWAL
    assert transaction.amount == Decimal("30.00")
    assert transaction.balance_after == Decimal("70.00")


def test_withdraw_rejects_overdraft_and_keeps_balance_unchanged():
    user = create_user("Alice", "81234567")
    deposit(user.account, Decimal("70.00"))

    with pytest.raises(InsufficientFundsError):
        withdraw(user.account, Decimal("100.00"))

    user.account.refresh_from_db()
    assert user.account.balance == Decimal("70.00")
    assert (
        Transaction.objects.filter(transaction_type=Transaction.WITHDRAWAL).count()
        == 0
    )


def test_withdraw_rejects_zero_amount():
    user = create_user("Alice", "81234567")

    with pytest.raises(InvalidAmountError):
        withdraw(user.account, Decimal("0.00"))


def test_valid_transfer_moves_funds_and_creates_two_transactions():
    alice = create_user("Alice", "81234567")
    bob = create_user("Bob", "91234567")
    deposit(alice.account, Decimal("200.00"))

    out_txn, in_txn = transfer(alice.account, "91234567", Decimal("50.00"))
    alice.account.refresh_from_db()
    bob.account.refresh_from_db()

    assert alice.account.balance == Decimal("150.00")
    assert bob.account.balance == Decimal("50.00")
    assert out_txn.transaction_type == Transaction.TRANSFER_OUT
    assert out_txn.counterparty == bob.account
    assert out_txn.balance_after == Decimal("150.00")
    assert in_txn.transaction_type == Transaction.TRANSFER_IN
    assert in_txn.counterparty == alice.account
    assert in_txn.balance_after == Decimal("50.00")


def test_transfer_exceeding_balance_rolls_back_all_changes():
    alice = create_user("Alice", "81234567")
    bob = create_user("Bob", "91234567")
    deposit(alice.account, Decimal("20.00"))

    with pytest.raises(InsufficientFundsError):
        transfer(alice.account, "91234567", Decimal("50.00"))

    alice.account.refresh_from_db()
    bob.account.refresh_from_db()
    assert alice.account.balance == Decimal("20.00")
    assert bob.account.balance == Decimal("0.00")
    assert (
        Transaction.objects.filter(transaction_type=Transaction.TRANSFER_OUT).count()
        == 0
    )
    assert (
        Transaction.objects.filter(transaction_type=Transaction.TRANSFER_IN).count()
        == 0
    )


def test_transfer_to_unknown_phone_raises_error():
    alice = create_user("Alice", "81234567")

    with pytest.raises(RecipientNotFoundError):
        transfer(alice.account, "91234567", Decimal("10.00"))


def test_transfer_to_self_raises_error():
    alice = create_user("Alice", "81234567")

    with pytest.raises(SelfTransferError):
        transfer(alice.account, "81234567", Decimal("10.00"))


@pytest.mark.parametrize("amount", [Decimal("0.00"), Decimal("-1.00")])
def test_transfer_rejects_non_positive_amount(amount):
    alice = create_user("Alice", "81234567")
    create_user("Bob", "91234567")

    with pytest.raises(InvalidAmountError):
        transfer(alice.account, "91234567", amount)
