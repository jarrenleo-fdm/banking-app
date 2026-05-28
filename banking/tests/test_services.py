"""Integration tests for atomic banking services."""
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model

from banking.models import Biller, Transaction
from banking.services import (
    InsufficientFundsError,
    InvalidAmountError,
    RecipientNotFoundError,
    SelfTransferError,
    deposit,
    pay_bill,
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


def test_transfer_with_description_stores_it_on_both_records():
    alice = create_user("Alice", "81234567")
    create_user("Bob", "91234567")
    deposit(alice.account, Decimal("100.00"))

    out_txn, in_txn = transfer(
        alice.account, "91234567", Decimal("30.00"), description="Rent May"
    )

    assert out_txn.description == "Rent May"
    assert in_txn.description == "Rent May"


def test_transfer_without_description_stores_empty_string():
    alice = create_user("Alice", "81234567")
    create_user("Bob", "91234567")
    deposit(alice.account, Decimal("100.00"))

    out_txn, in_txn = transfer(alice.account, "91234567", Decimal("30.00"))

    assert out_txn.description == ""
    assert in_txn.description == ""


# --- pay_bill service tests ---

def _make_biller(account, name=Biller.ELECTRICITY, reference="ACC-001"):
    return Biller.objects.create(account=account, name=name, reference=reference)


def test_pay_bill_deducts_balance_and_creates_bill_payment_transaction():
    user = create_user("Alice", "81234567")
    deposit(user.account, Decimal("100.00"))
    biller = _make_biller(user.account)

    txn = pay_bill(user.account, biller, Decimal("40.00"))
    user.account.refresh_from_db()

    assert user.account.balance == Decimal("60.00")
    assert txn.transaction_type == Transaction.BILL_PAYMENT
    assert txn.amount == Decimal("40.00")
    assert txn.balance_after == Decimal("60.00")
    assert txn.description == f"{biller.get_name_display()} ({biller.reference})"


def test_pay_bill_stores_biller_category_and_reference_in_description():
    user = create_user("Alice", "81234567")
    deposit(user.account, Decimal("50.00"))
    biller = _make_biller(user.account, name=Biller.INTERNET_BROADBAND)

    txn = pay_bill(user.account, biller, Decimal("20.00"))

    assert txn.description == "Internet & Broadband (ACC-001)"


def test_pay_bill_raises_insufficient_funds_and_leaves_balance_unchanged():
    user = create_user("Alice", "81234567")
    deposit(user.account, Decimal("30.00"))
    biller = _make_biller(user.account)

    with pytest.raises(InsufficientFundsError):
        pay_bill(user.account, biller, Decimal("50.00"))

    user.account.refresh_from_db()
    assert user.account.balance == Decimal("30.00")
    assert Transaction.objects.filter(
        transaction_type=Transaction.BILL_PAYMENT
    ).count() == 0


@pytest.mark.parametrize("amount", [Decimal("0.00"), Decimal("-1.00")])
def test_pay_bill_raises_invalid_amount_for_non_positive_values(amount):
    user = create_user("Alice", "81234567")
    deposit(user.account, Decimal("100.00"))
    biller = _make_biller(user.account)

    with pytest.raises(InvalidAmountError):
        pay_bill(user.account, biller, amount)

    user.account.refresh_from_db()
    assert user.account.balance == Decimal("100.00")
    assert Transaction.objects.filter(
        transaction_type=Transaction.BILL_PAYMENT
    ).count() == 0


# --- US1: create_business_account_mock service tests ---

def test_create_business_account_mock_creates_business_account():
    from banking.services import create_business_account_mock
    from banking.models import BusinessAccount
    create_business_account_mock("Acme Corp", "202512345A", "1 Marina Blvd", "Singapore", "018989", initial_deposit=Decimal("10000.00"))
    assert BusinessAccount.objects.filter(uen="202512345A").exists()


def test_create_business_account_mock_creates_manager_and_authoriser_users():
    from banking.services import create_business_account_mock
    from banking.models import AccountManagerProfile, Authoriser
    result = create_business_account_mock("Acme Corp", "202512345A", "1 Marina Blvd", "Singapore", "018989", initial_deposit=Decimal("10000.00"))
    assert AccountManagerProfile.objects.filter(user__username=result["manager_username"]).exists()
    assert Authoriser.objects.filter(user__username=result["authoriser_username"]).exists()


def test_create_business_account_mock_generates_sequential_phone_numbers():
    from banking.services import create_business_account_mock
    r1 = create_business_account_mock("Corp One", "UEN001", "1 St", "Singapore", "000001", initial_deposit=Decimal("10000.00"))
    r2 = create_business_account_mock("Corp Two", "UEN002", "2 St", "Singapore", "000002", initial_deposit=Decimal("10000.00"))
    assert r1["manager_phone"].startswith("8") or r1["manager_phone"].startswith("9")
    assert int(r1["manager_phone"]) % 2 == 1
    assert int(r1["authoriser_phone"]) % 2 == 0
    assert r1["manager_phone"] != r2["manager_phone"]
    assert r1["authoriser_phone"] != r2["authoriser_phone"]


def test_create_business_account_mock_returns_credentials_dict():
    from banking.services import create_business_account_mock
    result = create_business_account_mock("Acme Corp", "202512345A", "1 Marina Blvd", "Singapore", "018989", initial_deposit=Decimal("10000.00"))
    assert "manager_username" in result
    assert "manager_password" in result
    assert "manager_phone" in result
    assert "authoriser_username" in result
    assert "authoriser_password" in result
    assert "authoriser_phone" in result
    assert result["manager_password"].startswith("Demo@")
    assert result["authoriser_password"].startswith("Demo@")


def test_create_business_account_mock_duplicate_uen_raises():
    from banking.services import create_business_account_mock
    from django.db import IntegrityError
    create_business_account_mock("Acme Corp", "DUPE001", "1 St", "Singapore", "000001", initial_deposit=Decimal("10000.00"))
    with pytest.raises(IntegrityError):
        create_business_account_mock("Beta Corp", "DUPE001", "2 St", "Singapore", "000002", initial_deposit=Decimal("10000.00"))


def test_create_business_account_mock_collision_increments_username_suffix():
    from banking.services import create_business_account_mock
    r1 = create_business_account_mock("Acme", "UEN_COL1", "1 St", "Singapore", "000001", initial_deposit=Decimal("10000.00"))
    r2 = create_business_account_mock("Acme", "UEN_COL2", "1 St", "Singapore", "000002", initial_deposit=Decimal("10000.00"))
    assert r1["manager_username"] != r2["manager_username"]
    assert r1["authoriser_username"] != r2["authoriser_username"]


def test_create_business_account_mock_sets_balance_to_initial_deposit():
    from banking.services import create_business_account_mock
    from banking.models import BusinessAccount
    create_business_account_mock("Balance Co", "BAL001", "1 St", "Singapore", "000001", initial_deposit=Decimal("10000.00"))
    ba = BusinessAccount.objects.get(uen="BAL001")
    assert ba.balance == Decimal("10000.00")


def test_create_business_account_mock_records_initial_deposit_as_business_transaction():
    from banking.services import create_business_account_mock
    from banking.models import BusinessAccount, BusinessTransaction
    create_business_account_mock("Deposit Co", "DEP001", "1 St", "Singapore", "000001", initial_deposit=Decimal("10000.00"))
    ba = BusinessAccount.objects.get(uen="DEP001")
    assert BusinessTransaction.objects.filter(
        business_account=ba, transaction_type=BusinessTransaction.DEPOSIT, amount=Decimal("10000.00")
    ).exists()


def test_create_business_account_mock_initial_deposit_below_7000_raises():
    from banking.services import create_business_account_mock, BankingError
    with pytest.raises(BankingError):
        create_business_account_mock("Low Co", "LOW001", "1 St", "Singapore", "000001", initial_deposit=Decimal("6999.99"))


# --- US2: Manager transaction service tests ---

def make_business(company="Acme Corp", uen="UEN_TEST"):
    from banking.models import BusinessAccount, AccountManagerProfile, Authoriser
    User = get_user_model()
    ba = BusinessAccount.objects.create(
        company_name=company, uen=uen, street="1 St", city="Singapore", postal_code="000001"
    )
    mgr = User.objects.create_user(username=f"mgr_{uen}", email=f"mgr_{uen}@test.com",
                                    name="Manager", phone_number="80000001", password="Demo@abc123")
    auth = User.objects.create_user(username=f"auth_{uen}", email=f"auth_{uen}@test.com",
                                     name="Authoriser", phone_number="80000002", password="Demo@abc123")
    AccountManagerProfile.objects.create(user=mgr, business_account=ba)
    Authoriser.objects.create(user=auth, business_account=ba)
    return ba, mgr, auth


def test_deposit_to_business_increases_balance_and_creates_transaction():
    from banking.services import deposit_to_business
    from banking.models import BusinessTransaction
    ba, _, _ = make_business()
    txn = deposit_to_business(ba, Decimal("1000.00"))
    ba.refresh_from_db()
    assert ba.balance == Decimal("1000.00")
    assert txn.transaction_type == BusinessTransaction.DEPOSIT
    assert txn.amount == Decimal("1000.00")
    assert txn.balance_after == Decimal("1000.00")


def test_deposit_to_business_zero_amount_raises():
    from banking.services import deposit_to_business
    ba, _, _ = make_business()
    with pytest.raises(InvalidAmountError):
        deposit_to_business(ba, Decimal("0.00"))


def test_deposit_to_business_negative_amount_raises():
    from banking.services import deposit_to_business
    ba, _, _ = make_business()
    with pytest.raises(InvalidAmountError):
        deposit_to_business(ba, Decimal("-50.00"))


def test_create_pending_withdrawal_creates_pending_tx_status_pending():
    from banking.services import deposit_to_business, create_pending_withdrawal
    from banking.models import PendingTransaction
    ba, _, _ = make_business()
    deposit_to_business(ba, Decimal("8000.00"))
    ba.refresh_from_db()
    pt = create_pending_withdrawal(ba, Decimal("100.00"))
    assert pt.status == PendingTransaction.PENDING
    assert pt.transaction_type == PendingTransaction.WITHDRAWAL
    ba.refresh_from_db()
    assert ba.balance == Decimal("8000.00")


def test_create_pending_withdrawal_insufficient_funds_raises():
    from banking.services import create_pending_withdrawal
    ba, _, _ = make_business()
    with pytest.raises(InsufficientFundsError):
        create_pending_withdrawal(ba, Decimal("100.00"))


def test_create_pending_transfer_valid_creates_pending_tx():
    from banking.services import deposit_to_business, create_pending_transfer
    from banking.models import PendingTransaction
    ba, _, _ = make_business()
    deposit_to_business(ba, Decimal("8000.00"))
    ba.refresh_from_db()
    recipient = create_user("Recipient", "91234567")
    pt = create_pending_transfer(ba, Decimal("200.00"), "91234567")
    assert pt.status == PendingTransaction.PENDING
    assert pt.transaction_type == PendingTransaction.TRANSFER_OUT
    assert pt.counterparty == recipient.account


def test_create_pending_transfer_recipient_not_found_raises():
    from banking.services import deposit_to_business, create_pending_transfer
    ba, _, _ = make_business()
    deposit_to_business(ba, Decimal("8000.00"))
    ba.refresh_from_db()
    with pytest.raises(RecipientNotFoundError):
        create_pending_transfer(ba, Decimal("100.00"), "99999999")


def test_create_pending_transfer_insufficient_funds_raises():
    from banking.services import create_pending_transfer
    ba, _, _ = make_business()
    create_user("Recipient2", "91234567")
    with pytest.raises(InsufficientFundsError):
        create_pending_transfer(ba, Decimal("100.00"), "91234567")


def test_create_pending_withdrawal_minimum_balance_floor_raises():
    from banking.services import deposit_to_business, create_pending_withdrawal
    ba, _, _ = make_business(uen="FLOOR_WD")
    deposit_to_business(ba, Decimal("8000.00"))
    ba.refresh_from_db()
    with pytest.raises(InsufficientFundsError):
        create_pending_withdrawal(ba, Decimal("1500.00"))


def test_create_pending_transfer_minimum_balance_floor_raises():
    from banking.services import deposit_to_business, create_pending_transfer
    ba, _, _ = make_business(uen="FLOOR_TR")
    deposit_to_business(ba, Decimal("8000.00"))
    ba.refresh_from_db()
    create_user("FloorRecip", "92222222")
    with pytest.raises(InsufficientFundsError):
        create_pending_transfer(ba, Decimal("1500.00"), "92222222")


def test_create_pending_bill_payment_minimum_balance_floor_raises():
    from banking.services import deposit_to_business, create_pending_bill_payment
    ba, _, _ = make_business(uen="FLOOR_BP")
    deposit_to_business(ba, Decimal("8000.00"))
    ba.refresh_from_db()
    with pytest.raises(InsufficientFundsError):
        create_pending_bill_payment(ba, Decimal("1500.00"), "utilities", "ACC-001")


def test_create_pending_bill_payment_creates_pending_tx_with_description():
    from banking.services import deposit_to_business, create_pending_bill_payment
    from banking.models import PendingTransaction
    ba, _, _ = make_business()
    deposit_to_business(ba, Decimal("8000.00"))
    ba.refresh_from_db()
    pt = create_pending_bill_payment(ba, Decimal("50.00"), "utilities", "ACC-001")
    assert pt.status == PendingTransaction.PENDING
    assert pt.transaction_type == PendingTransaction.BILL_PAYMENT
    assert "utilities" in pt.description
    assert "ACC-001" in pt.description


# --- US3: Authoriser approve/reject service tests ---

def make_business_with_balance(balance=Decimal("8000.00")):
    from banking.services import deposit_to_business
    ba, mgr, auth_user = make_business(company="TestCo", uen="US3_UEN")
    ba.refresh_from_db()
    deposit_to_business(ba, balance)
    ba.refresh_from_db()
    return ba, mgr, auth_user


def test_approve_business_pending_sets_status_approved():
    from banking.services import approve_business_pending
    from banking.models import PendingTransaction
    ba, _, auth_user = make_business_with_balance()
    pt = PendingTransaction.objects.create(
        business_account=ba, transaction_type=PendingTransaction.WITHDRAWAL, amount=Decimal("100.00")
    )
    approve_business_pending(pt, auth_user)
    pt.refresh_from_db()
    assert pt.status == PendingTransaction.APPROVED
    assert pt.decided_by == auth_user
    assert pt.decided_at is not None


def test_approve_business_pending_updates_business_account_balance():
    from banking.services import approve_business_pending
    from banking.models import PendingTransaction
    ba, _, auth_user = make_business_with_balance(Decimal("8000.00"))
    pt = PendingTransaction.objects.create(
        business_account=ba, transaction_type=PendingTransaction.WITHDRAWAL, amount=Decimal("1000.00")
    )
    approve_business_pending(pt, auth_user)
    ba.refresh_from_db()
    assert ba.balance == Decimal("7000.00")


def test_approve_business_pending_creates_business_transaction():
    from banking.services import approve_business_pending
    from banking.models import PendingTransaction, BusinessTransaction
    ba, _, auth_user = make_business_with_balance()
    pt = PendingTransaction.objects.create(
        business_account=ba, transaction_type=PendingTransaction.WITHDRAWAL, amount=Decimal("500.00")
    )
    approve_business_pending(pt, auth_user)
    assert BusinessTransaction.objects.filter(
        business_account=ba, transaction_type=BusinessTransaction.WITHDRAWAL
    ).exists()


def test_approve_business_pending_auto_rejects_when_floor_breached():
    from banking.services import approve_business_pending
    from banking.models import PendingTransaction
    ba, _, auth_user = make_business(company="BreakCo", uen="BREAK_UEN")
    pt = PendingTransaction.objects.create(
        business_account=ba, transaction_type=PendingTransaction.WITHDRAWAL, amount=Decimal("9999.00")
    )
    result = approve_business_pending(pt, auth_user)
    assert result is False
    pt.refresh_from_db()
    assert pt.status == PendingTransaction.REJECTED


def test_approve_business_pending_returns_true_on_success():
    from banking.services import approve_business_pending
    from banking.models import PendingTransaction
    ba, _, auth_user = make_business_with_balance(Decimal("8000.00"))
    pt = PendingTransaction.objects.create(
        business_account=ba, transaction_type=PendingTransaction.WITHDRAWAL, amount=Decimal("100.00")
    )
    result = approve_business_pending(pt, auth_user)
    assert result is True
    pt.refresh_from_db()
    assert pt.status == PendingTransaction.APPROVED


def test_approve_business_pending_auto_rejects_records_business_transaction():
    from banking.services import approve_business_pending
    from banking.models import PendingTransaction, BusinessTransaction
    ba, _, auth_user = make_business(company="ZeroCo", uen="ZERO_UEN")
    pt = PendingTransaction.objects.create(
        business_account=ba, transaction_type=PendingTransaction.WITHDRAWAL, amount=Decimal("9999.00")
    )
    approve_business_pending(pt, auth_user)
    assert BusinessTransaction.objects.filter(
        business_account=ba, transaction_type=BusinessTransaction.REJECTED
    ).exists()


def test_reject_business_pending_sets_status_rejected():
    from banking.services import reject_business_pending
    from banking.models import PendingTransaction
    ba, _, auth_user = make_business_with_balance()
    pt = PendingTransaction.objects.create(
        business_account=ba, transaction_type=PendingTransaction.WITHDRAWAL, amount=Decimal("100.00")
    )
    reject_business_pending(pt, auth_user)
    pt.refresh_from_db()
    assert pt.status == PendingTransaction.REJECTED
    assert pt.decided_by == auth_user


def test_reject_business_pending_creates_rejected_business_transaction():
    from banking.services import reject_business_pending
    from banking.models import PendingTransaction, BusinessTransaction
    ba, _, auth_user = make_business_with_balance()
    pt = PendingTransaction.objects.create(
        business_account=ba, transaction_type=PendingTransaction.WITHDRAWAL, amount=Decimal("200.00")
    )
    reject_business_pending(pt, auth_user)
    assert BusinessTransaction.objects.filter(
        business_account=ba, transaction_type=BusinessTransaction.REJECTED
    ).exists()


def test_reject_business_pending_balance_unchanged():
    from banking.services import reject_business_pending
    from banking.models import PendingTransaction
    ba, _, auth_user = make_business_with_balance(Decimal("3000.00"))
    pt = PendingTransaction.objects.create(
        business_account=ba, transaction_type=PendingTransaction.WITHDRAWAL, amount=Decimal("500.00")
    )
    reject_business_pending(pt, auth_user)
    ba.refresh_from_db()
    assert ba.balance == Decimal("3000.00")


# --- US4: Authoriser immediate-execution service tests ---

def _make_auth_ba(uen="US4_UEN", balance=Decimal("10000.00")):
    from banking.services import deposit_to_business
    ba, mgr, auth_user = make_business(company="AuthCo", uen=uen)
    deposit_to_business(ba, balance)
    ba.refresh_from_db()
    return ba, mgr, auth_user


def test_withdraw_from_business_deducts_balance_and_creates_transaction():
    from banking.services import withdraw_from_business
    from banking.models import BusinessTransaction
    ba, _, _ = _make_auth_ba()
    txn = withdraw_from_business(ba, Decimal("2000.00"))
    ba.refresh_from_db()
    assert ba.balance == Decimal("8000.00")
    assert txn.transaction_type == BusinessTransaction.WITHDRAWAL
    assert txn.amount == Decimal("2000.00")
    assert txn.balance_after == Decimal("8000.00")


def test_withdraw_from_business_zero_amount_raises():
    from banking.services import withdraw_from_business
    ba, _, _ = _make_auth_ba(uen="US4_ZERO")
    with pytest.raises(InvalidAmountError):
        withdraw_from_business(ba, Decimal("0.00"))


def test_withdraw_from_business_floor_breach_raises():
    from banking.services import withdraw_from_business
    ba, _, _ = _make_auth_ba(uen="US4_FLOOR")
    with pytest.raises(InsufficientFundsError):
        withdraw_from_business(ba, Decimal("4000.00"))
    ba.refresh_from_db()
    assert ba.balance == Decimal("10000.00")


def test_withdraw_from_business_exact_floor_succeeds():
    from banking.services import withdraw_from_business
    ba, _, _ = _make_auth_ba(uen="US4_EXACT")
    txn = withdraw_from_business(ba, Decimal("3000.00"))
    ba.refresh_from_db()
    assert ba.balance == Decimal("7000.00")
    assert txn.balance_after == Decimal("7000.00")


def test_transfer_from_business_executes_immediately_and_creates_transaction():
    from banking.services import transfer_from_business
    from banking.models import BusinessTransaction, PendingTransaction
    ba, _, _ = _make_auth_ba(uen="US4_TR")
    recipient = create_user("TrRecipient", "91234567")
    txn = transfer_from_business(ba, Decimal("500.00"), "91234567")
    ba.refresh_from_db()
    recipient.account.refresh_from_db()
    assert ba.balance == Decimal("9500.00")
    assert recipient.account.balance == Decimal("500.00")
    assert txn.transaction_type == BusinessTransaction.TRANSFER_OUT
    assert PendingTransaction.objects.filter(business_account=ba).count() == 0


def test_transfer_from_business_recipient_not_found_raises():
    from banking.services import transfer_from_business
    ba, _, _ = _make_auth_ba(uen="US4_NF")
    with pytest.raises(RecipientNotFoundError):
        transfer_from_business(ba, Decimal("100.00"), "99999999")


def test_transfer_from_business_floor_breach_raises():
    from banking.services import transfer_from_business
    ba, _, _ = _make_auth_ba(uen="US4_TRF")
    create_user("FloorRecipient", "92222222")
    with pytest.raises(InsufficientFundsError):
        transfer_from_business(ba, Decimal("4000.00"), "92222222")
    ba.refresh_from_db()
    assert ba.balance == Decimal("10000.00")


def test_pay_bill_from_business_creates_transaction_with_description():
    from banking.services import pay_bill_from_business
    from banking.models import BusinessTransaction
    ba, _, _ = _make_auth_ba(uen="US4_BILL")
    txn = pay_bill_from_business(ba, Decimal("200.00"), "utilities", "ACC-001")
    ba.refresh_from_db()
    assert ba.balance == Decimal("9800.00")
    assert txn.transaction_type == BusinessTransaction.BILL_PAYMENT
    assert "utilities" in txn.description
    assert "ACC-001" in txn.description


def test_pay_bill_from_business_floor_breach_raises():
    from banking.services import pay_bill_from_business
    ba, _, _ = _make_auth_ba(uen="US4_BILLF")
    with pytest.raises(InsufficientFundsError):
        pay_bill_from_business(ba, Decimal("4000.00"), "utilities", "ACC-001")
    ba.refresh_from_db()
    assert ba.balance == Decimal("10000.00")
