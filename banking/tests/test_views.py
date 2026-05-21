"""Integration tests for banking views."""
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.urls import reverse

from banking.models import Biller, Transaction
from banking.services import deposit, pay_bill, transfer, withdraw


User = get_user_model()


def create_user(username, phone_number, email=None):
    return User.objects.create_user(
        username=username,
        email=email or f"{username.lower()}@example.com",
        name=f"{username} Example",
        phone_number=phone_number,
        password="StrongerPass123",
    )


def login(client, user):
    client.force_login(user)


def test_authenticated_dashboard_shows_balance(client):
    user = create_user("Alice", "81234567")
    login(client, user)

    response = client.get(reverse("banking:dashboard"))

    assert response.status_code == 200
    assert b"0.00" in response.content


def test_post_deposit_changes_balance_and_redirects(client):
    user = create_user("Alice", "81234567")
    login(client, user)

    response = client.post(reverse("banking:deposit"), {"amount": "100.00"})
    user.account.refresh_from_db()

    assert response.status_code == 302
    assert user.account.balance == Decimal("100.00")


def test_post_deposit_with_negative_amount_is_rejected(client):
    user = create_user("Alice", "81234567")
    login(client, user)

    response = client.post(reverse("banking:deposit"), {"amount": "-1.00"})
    user.account.refresh_from_db()

    assert response.status_code == 200
    assert user.account.balance == Decimal("0.00")


def test_post_withdraw_changes_balance_and_redirects(client):
    user = create_user("Alice", "81234567")
    deposit(user.account, Decimal("100.00"))
    login(client, user)

    response = client.post(reverse("banking:withdraw"), {"amount": "30.00"})
    user.account.refresh_from_db()

    assert response.status_code == 302
    assert user.account.balance == Decimal("70.00")


def test_post_withdraw_exceeding_balance_is_rejected(client):
    user = create_user("Alice", "81234567")
    deposit(user.account, Decimal("70.00"))
    login(client, user)

    response = client.post(reverse("banking:withdraw"), {"amount": "100.00"})
    user.account.refresh_from_db()

    assert response.status_code == 200
    assert b"Insufficient funds" in response.content
    assert user.account.balance == Decimal("70.00")


def test_valid_transfer_post_redirects_with_success(client):
    alice = create_user("Alice", "81234567")
    bob = create_user("Bob", "91234567")
    deposit(alice.account, Decimal("200.00"))
    login(client, alice)

    response = client.post(
        reverse("banking:transfer"),
        {"recipient_phone": bob.phone_number, "amount": "50.00"},
    )
    alice.account.refresh_from_db()
    bob.account.refresh_from_db()

    assert response.status_code == 302
    assert alice.account.balance == Decimal("150.00")
    assert bob.account.balance == Decimal("50.00")


def test_transfer_post_with_insufficient_funds_shows_error(client):
    alice = create_user("Alice", "81234567")
    bob = create_user("Bob", "91234567")
    login(client, alice)

    response = client.post(
        reverse("banking:transfer"),
        {"recipient_phone": bob.phone_number, "amount": "50.00"},
    )

    assert response.status_code == 200
    assert b"Insufficient funds" in response.content


def test_transfer_post_to_unknown_recipient_shows_error(client):
    alice = create_user("Alice", "81234567")
    login(client, alice)

    response = client.post(
        reverse("banking:transfer"),
        {"recipient_phone": "91234567", "amount": "10.00"},
    )

    assert response.status_code == 200
    assert b"No account found with that phone number" in response.content


def test_transfer_post_to_self_shows_error(client):
    alice = create_user("Alice", "81234567")
    deposit(alice.account, Decimal("50.00"))
    login(client, alice)

    response = client.post(
        reverse("banking:transfer"),
        {"recipient_phone": "81234567", "amount": "10.00"},
    )

    assert response.status_code == 200
    assert b"Cannot transfer to your own account" in response.content


def test_transfer_post_with_invalid_amount_shows_error(client):
    alice = create_user("Alice", "81234567")
    bob = create_user("Bob", "91234567")
    login(client, alice)

    response = client.post(
        reverse("banking:transfer"),
        {"recipient_phone": bob.phone_number, "amount": "0.00"},
    )

    assert response.status_code == 200
    assert b"Ensure this value is greater than or equal to 0.01" in response.content


def test_unauthenticated_transfer_post_redirects_to_login(client):
    response = client.post(
        reverse("banking:transfer"),
        {"recipient_phone": "91234567", "amount": "10.00"},
    )

    assert response.status_code == 302
    assert response.url == (
        f"{reverse('accounts:login')}?next={reverse('banking:transfer')}"
    )


def test_transaction_history_shows_user_transactions_ordered_newest_first(client):
    alice = create_user("Alice", "81234567")
    bob = create_user("Bob", "91234567")
    deposit(alice.account, Decimal("100.00"))
    withdraw(alice.account, Decimal("20.00"))
    transfer(alice.account, "91234567", Decimal("30.00"))
    login(client, alice)

    response = client.get(reverse("banking:transactions"))
    transactions = list(response.context["transactions"])

    assert response.status_code == 200
    assert [txn.transaction_type for txn in transactions] == [
        Transaction.TRANSFER_OUT,
        Transaction.WITHDRAWAL,
        Transaction.DEPOSIT,
    ]
    assert transactions[0].counterparty == bob.account
    assert b"Bob Example" in response.content
    assert b"91234567" in response.content


def test_transaction_history_empty_state(client):
    user = create_user("Alice", "81234567")
    login(client, user)

    response = client.get(reverse("banking:transactions"))

    assert response.status_code == 200
    assert b"You have no transactions yet." in response.content


def test_transaction_history_excludes_other_users_transactions(client):
    alice = create_user("Alice", "81234567")
    bob = create_user("Bob", "91234567")
    deposit(bob.account, Decimal("40.00"))
    login(client, alice)

    response = client.get(reverse("banking:transactions"))

    assert not list(response.context["transactions"])


def test_unauthenticated_transaction_history_redirects_to_login(client):
    response = client.get(reverse("banking:transactions"))

    assert response.status_code == 302
    assert response.url == (
        f"{reverse('accounts:login')}?next={reverse('banking:transactions')}"
    )


def test_transaction_history_shows_to_label_for_outgoing_transfer(client):
    alice = create_user("Alice", "81234567")
    create_user("Bob", "91234567")
    deposit(alice.account, Decimal("100.00"))
    transfer(alice.account, "91234567", Decimal("30.00"))
    login(client, alice)

    response = client.get(reverse("banking:transactions"))

    assert response.status_code == 200
    assert b"To:" in response.content
    assert b"Bob Example" in response.content


def test_transaction_history_shows_from_label_for_incoming_transfer(client):
    alice = create_user("Alice", "81234567")
    bob = create_user("Bob", "91234567")
    deposit(alice.account, Decimal("100.00"))
    transfer(alice.account, "91234567", Decimal("30.00"))
    login(client, bob)

    response = client.get(reverse("banking:transactions"))

    assert response.status_code == 200
    assert b"From:" in response.content
    assert b"Alice Example" in response.content


def test_transaction_history_shows_no_counterparty_for_deposit(client):
    alice = create_user("Alice", "81234567")
    deposit(alice.account, Decimal("50.00"))
    login(client, alice)

    response = client.get(reverse("banking:transactions"))

    assert response.status_code == 200
    assert b"From:" not in response.content
    assert b"To:" not in response.content


def test_transaction_history_shows_transaction_id_for_each_entry(client):
    alice = create_user("Alice", "81234567")
    create_user("Bob", "91234567")
    deposit(alice.account, Decimal("100.00"))
    transfer(alice.account, "91234567", Decimal("20.00"))
    login(client, alice)

    response = client.get(reverse("banking:transactions"))
    transactions = list(response.context["transactions"])

    assert response.status_code == 200
    assert len(transactions) == 2
    for txn in transactions:
        assert f"#{txn.pk}".encode() in response.content


def test_transaction_history_ids_are_unique_across_entries(client):
    alice = create_user("Alice", "81234567")
    deposit(alice.account, Decimal("100.00"))
    deposit(alice.account, Decimal("50.00"))
    login(client, alice)

    response = client.get(reverse("banking:transactions"))
    transactions = list(response.context["transactions"])

    assert transactions[0].pk != transactions[1].pk


def test_transfer_with_description_shows_in_sender_history(client):
    alice = create_user("Alice", "81234567")
    bob = create_user("Bob", "91234567")
    deposit(alice.account, Decimal("100.00"))
    login(client, alice)

    client.post(
        reverse("banking:transfer"),
        {
            "recipient_phone": bob.phone_number,
            "amount": "30.00",
            "description": "Rent May",
        },
    )

    response = client.get(reverse("banking:transactions"))
    assert b"Rent May" in response.content


def test_transfer_with_description_shows_in_recipient_history(client):
    alice = create_user("Alice", "81234567")
    bob = create_user("Bob", "91234567")
    deposit(alice.account, Decimal("100.00"))
    transfer(alice.account, "91234567", Decimal("30.00"), description="Rent May")
    login(client, bob)

    response = client.get(reverse("banking:transactions"))
    assert b"Rent May" in response.content


def test_transfer_without_description_shows_no_description_label(client):
    alice = create_user("Alice", "81234567")
    create_user("Bob", "91234567")
    deposit(alice.account, Decimal("100.00"))
    transfer(alice.account, "91234567", Decimal("30.00"))
    login(client, alice)

    response = client.get(reverse("banking:transactions"))
    assert b"Description:" not in response.content


# --- Dashboard account type label tests (T010) ---

def test_dashboard_shows_business_label_for_business_account(client):
    from banking.models import Account, BusinessProfile

    user = create_user("Corp", "81234567")
    user.account.account_type = Account.BUSINESS
    user.account.save(update_fields=["account_type"])
    BusinessProfile.objects.create(
        account=user.account,
        company_name="Corp Pte Ltd",
        business_registration_number="ABC12345",
    )
    login(client, user)

    response = client.get(reverse("banking:dashboard"))

    assert response.status_code == 200
    assert b"Business" in response.content


def test_dashboard_shows_personal_label_for_personal_account(client):
    user = create_user("Alice", "81234567")
    login(client, user)

    response = client.get(reverse("banking:dashboard"))

    assert response.status_code == 200
    assert b"Personal" in response.content


# --- US1: Pay a Bill view tests ---

def _make_biller(account, name="SP PowerGrid", reference="ACC-001"):
    return Biller.objects.create(account=account, name=name, reference=reference)


def test_billing_page_renders_for_authenticated_user(client):
    user = create_user("Alice", "81234567")
    login(client, user)

    response = client.get(reverse("banking:billing"))

    assert response.status_code == 200
    assert "billers" in response.context
    assert "pay_form" in response.context


def test_billing_page_unauthenticated_redirects_to_login(client):
    response = client.get(reverse("banking:billing"))

    assert response.status_code == 302
    assert reverse("accounts:login") in response.url


def test_pay_bill_view_valid_payment_redirects_and_decrements_balance(client):
    user = create_user("Alice", "81234567")
    deposit(user.account, Decimal("100.00"))
    biller = _make_biller(user.account)
    login(client, user)

    response = client.post(
        reverse("banking:pay_bill"),
        {"biller": biller.pk, "amount": "40.00"},
    )
    user.account.refresh_from_db()

    assert response.status_code == 302
    assert user.account.balance == Decimal("60.00")


def test_pay_bill_view_insufficient_funds_shows_form_error(client):
    user = create_user("Alice", "81234567")
    biller = _make_biller(user.account)
    login(client, user)

    response = client.post(
        reverse("banking:pay_bill"),
        {"biller": biller.pk, "amount": "50.00"},
    )
    user.account.refresh_from_db()

    assert response.status_code == 200
    assert b"Insufficient funds" in response.content
    assert user.account.balance == Decimal("0.00")


def test_pay_bill_view_zero_amount_shows_form_error(client):
    user = create_user("Alice", "81234567")
    biller = _make_biller(user.account)
    login(client, user)

    response = client.post(
        reverse("banking:pay_bill"),
        {"biller": biller.pk, "amount": "0.00"},
    )

    assert response.status_code == 200


def test_pay_bill_view_rejects_another_users_biller(client):
    alice = create_user("Alice", "81234567")
    bob = create_user("Bob", "91234567")
    deposit(alice.account, Decimal("100.00"))
    bob_biller = _make_biller(bob.account, name="Bob's biller")
    login(client, alice)

    response = client.post(
        reverse("banking:pay_bill"),
        {"biller": bob_biller.pk, "amount": "10.00"},
    )
    alice.account.refresh_from_db()

    assert response.status_code == 200
    assert alice.account.balance == Decimal("100.00")


# --- US2: Manage Saved Billers view tests ---

def test_add_biller_creates_biller_and_redirects(client):
    user = create_user("Alice", "81234567")
    login(client, user)

    response = client.post(
        reverse("banking:add_biller"),
        {"name": "SP PowerGrid", "reference": "ACC-001"},
    )

    assert response.status_code == 302
    assert user.account.billers.filter(name="SP PowerGrid").exists()


def test_add_biller_with_blank_name_shows_error(client):
    user = create_user("Alice", "81234567")
    login(client, user)

    response = client.post(
        reverse("banking:add_biller"),
        {"name": "   ", "reference": ""},
    )

    assert response.status_code == 200
    assert user.account.billers.count() == 0


def test_remove_biller_deletes_own_biller_and_redirects(client):
    user = create_user("Alice", "81234567")
    biller = _make_biller(user.account)
    login(client, user)

    response = client.post(reverse("banking:remove_biller", args=[biller.pk]))

    assert response.status_code == 302
    assert not user.account.billers.filter(pk=biller.pk).exists()


def test_remove_biller_rejects_another_users_biller_with_404(client):
    alice = create_user("Alice", "81234567")
    bob = create_user("Bob", "91234567")
    bob_biller = _make_biller(bob.account)
    login(client, alice)

    response = client.post(reverse("banking:remove_biller", args=[bob_biller.pk]))

    assert response.status_code == 404
    assert bob.account.billers.filter(pk=bob_biller.pk).exists()


# --- US3: Billing History view tests ---

def test_billing_history_shows_bill_payments_newest_first(client):
    user = create_user("Alice", "81234567")
    deposit(user.account, Decimal("200.00"))
    biller = _make_biller(user.account)
    pay_bill(user.account, biller, Decimal("30.00"))
    pay_bill(user.account, biller, Decimal("20.00"))
    login(client, user)

    response = client.get(reverse("banking:billing_history"))
    payments = list(response.context["payments"])

    assert response.status_code == 200
    assert len(payments) == 2
    assert payments[0].amount == Decimal("20.00")
    assert payments[1].amount == Decimal("30.00")


def test_billing_history_excludes_non_bill_payment_transactions(client):
    user = create_user("Alice", "81234567")
    deposit(user.account, Decimal("100.00"))
    withdraw(user.account, Decimal("10.00"))
    login(client, user)

    response = client.get(reverse("banking:billing_history"))

    assert response.status_code == 200
    assert list(response.context["payments"]) == []


def test_billing_history_empty_state(client):
    user = create_user("Alice", "81234567")
    login(client, user)

    response = client.get(reverse("banking:billing_history"))

    assert response.status_code == 200
    assert b"no bill payments" in response.content.lower()


def test_billing_history_excludes_other_users_payments(client):
    alice = create_user("Alice", "81234567")
    bob = create_user("Bob", "91234567")
    deposit(bob.account, Decimal("100.00"))
    bob_biller = _make_biller(bob.account)
    pay_bill(bob.account, bob_biller, Decimal("20.00"))
    login(client, alice)

    response = client.get(reverse("banking:billing_history"))

    assert list(response.context["payments"]) == []
