"""Integration tests for banking views."""
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.urls import reverse

from banking.models import Transaction
from banking.services import deposit, transfer, withdraw


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
