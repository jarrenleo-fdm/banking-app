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


def test_transfer_uses_updated_recipient_phone_number(client):
    alice = create_user("Alice", "81234567")
    bob = create_user("Bob", "91234567")
    bob.phone_number = "91239999"
    bob.save(update_fields=["phone_number"])
    deposit(alice.account, Decimal("100.00"))
    login(client, alice)

    response = client.post(
        reverse("banking:transfer"),
        {"recipient_phone": "91239999", "amount": "25.00"},
    )
    alice.account.refresh_from_db()
    bob.account.refresh_from_db()

    assert response.status_code == 302
    assert alice.account.balance == Decimal("75.00")
    assert bob.account.balance == Decimal("25.00")


# --- US1: Pay a Bill view tests ---

def _make_biller(account, name=Biller.ELECTRICITY, reference="ACC-001"):
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
    bob_biller = _make_biller(bob.account, name=Biller.TELECOMMUNICATIONS)
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
        {"name": "ELECTRICITY", "reference": "ACC-001"},
    )

    assert response.status_code == 302
    assert user.account.billers.filter(name=Biller.ELECTRICITY).exists()


def test_add_biller_with_blank_name_shows_error(client):
    user = create_user("Alice", "81234567")
    login(client, user)

    response = client.post(
        reverse("banking:add_biller"),
        {"name": "", "reference": ""},
    )

    assert response.status_code == 200
    assert user.account.billers.count() == 0


def test_add_biller_rejects_invalid_category_string(client):
    user = create_user("Alice", "81234567")
    login(client, user)

    response = client.post(
        reverse("banking:add_biller"),
        {"name": "Fake Biller", "reference": ""},
    )

    assert response.status_code == 200
    assert user.account.billers.count() == 0


def test_add_biller_rejects_blank_reference(client):
    user = create_user("Alice", "81234567")
    login(client, user)

    response = client.post(
        reverse("banking:add_biller"),
        {"name": "ELECTRICITY", "reference": ""},
    )

    assert response.status_code == 200
    assert user.account.billers.count() == 0
    assert b"reference" in response.content.lower()


def test_add_biller_rejects_duplicate_reference_same_category(client):
    user = create_user("Alice", "81234567")
    Biller.objects.create(
        account=user.account, name=Biller.ELECTRICITY, reference="ACC-001"
    )
    login(client, user)

    response = client.post(
        reverse("banking:add_biller"),
        {"name": "ELECTRICITY", "reference": "ACC-001"},
    )

    assert response.status_code == 200
    assert user.account.billers.count() == 1
    assert b"already exists" in response.content.lower()


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


# --- US1: Business account creation view tests ---

def test_create_business_account_view_get_renders_form(client):
    from django.urls import reverse
    response = client.get(reverse("banking:create_business_account"))
    assert response.status_code == 200
    assert b"company_name" in response.content


def test_create_business_account_view_post_valid_redirects_to_created(client):
    from django.urls import reverse
    response = client.post(reverse("banking:create_business_account"), {
        "company_name": "Acme Corp",
        "uen": "202512345A",
        "street": "1 Marina Boulevard",
        "city": "Singapore",
        "postal_code": "018989",
        "initial_deposit": "10000.00",
    })
    assert response.status_code == 302
    assert "/business/created/" in response.url


def test_create_business_account_view_post_blank_field_returns_error(client):
    from django.urls import reverse
    response = client.post(reverse("banking:create_business_account"), {
        "company_name": "",
        "uen": "202512345A",
        "street": "1 Marina Boulevard",
        "city": "Singapore",
        "postal_code": "018989",
    })
    assert response.status_code == 200
    assert b"errorlist" in response.content


def test_create_business_account_view_post_duplicate_uen_returns_error(client):
    from django.urls import reverse
    from banking.services import create_business_account_mock
    create_business_account_mock("Acme Corp", "202512345A", "1 Marina Blvd", "Singapore", "018989", initial_deposit=Decimal("10000.00"))
    response = client.post(reverse("banking:create_business_account"), {
        "company_name": "Beta Corp",
        "uen": "202512345A",
        "street": "2 Marina Boulevard",
        "city": "Singapore",
        "postal_code": "018989",
        "initial_deposit": "10000.00",
    })
    assert response.status_code == 200
    assert b"already exists" in response.content


def test_business_account_created_view_with_credentials_in_session(client):
    from django.urls import reverse
    from banking.models import BusinessAccount
    from banking.services import create_business_account_mock
    creds = create_business_account_mock("Acme Corp", "202512345A", "1 Marina Blvd", "Singapore", "018989", initial_deposit=Decimal("10000.00"))
    ba = BusinessAccount.objects.get(uen="202512345A")
    session = client.session
    session["business_created_credentials"] = creds
    session.save()
    response = client.get(reverse("banking:business_account_created") + f"?id={ba.pk}")
    assert response.status_code == 200
    assert creds["manager_username"].encode() in response.content


def test_business_account_created_view_no_session_redirects_to_create(client):
    from django.urls import reverse
    response = client.get(reverse("banking:business_account_created"))
    assert response.status_code == 302
    assert "/business/create/" in response.url


def test_business_account_created_view_clears_session_after_display(client):
    from django.urls import reverse
    from banking.models import BusinessAccount
    from banking.services import create_business_account_mock
    creds = create_business_account_mock("Acme Corp", "202512345A", "1 Marina Blvd", "Singapore", "018989", initial_deposit=Decimal("10000.00"))
    ba = BusinessAccount.objects.get(uen="202512345A")
    session = client.session
    session["business_created_credentials"] = creds
    session.save()
    client.get(reverse("banking:business_account_created") + f"?id={ba.pk}")
    assert "business_created_credentials" not in client.session


# --- US2: Manager transaction view tests ---

def make_business_setup():
    """Create a BusinessAccount with manager and authoriser users."""
    from django.contrib.auth import get_user_model
    from banking.models import BusinessAccount, AccountManagerProfile, Authoriser
    User = get_user_model()
    ba = BusinessAccount.objects.create(
        company_name="Acme Corp", uen="UEN001",
        street="1 St", city="Singapore", postal_code="000001",
    )
    mgr = User.objects.create_user(
        username="manager.acme", email="mgr@acme.com", name="Manager",
        phone_number="80000001", password="Demo@abc123",
    )
    auth_user = User.objects.create_user(
        username="authoriser.acme", email="auth@acme.com", name="Authoriser",
        phone_number="80000002", password="Demo@abc123",
    )
    AccountManagerProfile.objects.create(user=mgr, business_account=ba)
    Authoriser.objects.create(user=auth_user, business_account=ba)
    return ba, mgr, auth_user


def test_dashboard_view_as_account_manager_shows_business_account(client):
    ba, mgr, _ = make_business_setup()
    client.force_login(mgr)
    response = client.get(reverse("banking:dashboard"))
    assert response.status_code == 200
    assert response.context["is_manager"] is True
    assert response.context["business_account"] == ba


def test_dashboard_view_as_personal_user_unchanged(client):
    user = create_user("PersonalUser", "91234567")
    client.force_login(user)
    response = client.get(reverse("banking:dashboard"))
    assert response.status_code == 200
    assert not response.context.get("is_manager")


def test_deposit_view_as_account_manager_updates_balance(client):
    from banking.models import BusinessTransaction
    ba, mgr, _ = make_business_setup()
    client.force_login(mgr)
    response = client.post(reverse("banking:deposit"), {"amount": "5000.00"})
    ba.refresh_from_db()
    assert response.status_code == 302
    assert ba.balance == Decimal("5000.00")
    assert BusinessTransaction.objects.filter(business_account=ba, transaction_type=BusinessTransaction.DEPOSIT).exists()


def test_withdraw_view_as_account_manager_creates_pending_balance_unchanged(client):
    from banking.models import BusinessTransaction, PendingTransaction
    from banking.services import deposit_to_business
    ba, mgr, _ = make_business_setup()
    ba.refresh_from_db()
    deposit_to_business(ba, Decimal("8000.00"))
    ba.refresh_from_db()
    client.force_login(mgr)
    response = client.post(reverse("banking:withdraw"), {"amount": "1000.00"})
    ba.refresh_from_db()
    assert response.status_code == 302
    assert ba.balance == Decimal("8000.00")
    assert PendingTransaction.objects.filter(business_account=ba, status=PendingTransaction.PENDING).exists()


def test_withdraw_view_as_account_manager_insufficient_funds(client):
    from banking.models import PendingTransaction
    ba, mgr, _ = make_business_setup()
    client.force_login(mgr)
    response = client.post(reverse("banking:withdraw"), {"amount": "1000.00"})
    ba.refresh_from_db()
    assert response.status_code == 200
    assert b"minimum" in response.content
    assert ba.balance == Decimal("0.00")
    assert not PendingTransaction.objects.filter(business_account=ba).exists()


def test_transfer_view_as_account_manager_creates_pending(client):
    from banking.models import PendingTransaction
    from banking.services import deposit_to_business
    ba, mgr, _ = make_business_setup()
    ba.refresh_from_db()
    deposit_to_business(ba, Decimal("8000.00"))
    ba.refresh_from_db()
    recipient = create_user("Recipient", "91234567")
    client.force_login(mgr)
    response = client.post(reverse("banking:transfer"), {"recipient_phone": "91234567", "amount": "500.00"})
    assert response.status_code == 302
    ba.refresh_from_db()
    assert ba.balance == Decimal("8000.00")
    assert PendingTransaction.objects.filter(business_account=ba, transaction_type=PendingTransaction.TRANSFER_OUT).exists()


def test_transfer_view_as_account_manager_recipient_not_found(client):
    from banking.services import deposit_to_business
    ba, mgr, _ = make_business_setup()
    ba.refresh_from_db()
    deposit_to_business(ba, Decimal("8000.00"))
    ba.refresh_from_db()
    client.force_login(mgr)
    response = client.post(reverse("banking:transfer"), {"recipient_phone": "99999999", "amount": "500.00"})
    assert response.status_code == 200
    assert b"No account found with that phone number" in response.content


def test_pay_bill_view_as_account_manager_creates_pending(client):
    from banking.models import PendingTransaction
    from banking.services import deposit_to_business
    ba, mgr, _ = make_business_setup()
    ba.refresh_from_db()
    deposit_to_business(ba, Decimal("8000.00"))
    ba.refresh_from_db()
    client.force_login(mgr)
    response = client.post(reverse("banking:pay_bill"), {
        "category": "utilities", "reference": "ACC-001", "amount": "200.00"
    })
    assert response.status_code == 302
    ba.refresh_from_db()
    assert ba.balance == Decimal("8000.00")
    assert PendingTransaction.objects.filter(business_account=ba, transaction_type=PendingTransaction.BILL_PAYMENT).exists()


def test_transaction_history_as_account_manager_shows_business_transactions(client):
    from banking.models import BusinessTransaction

    ba, mgr, _ = make_business_setup()
    personal_txn = deposit(mgr.account, Decimal("25.00"))
    business_txn = BusinessTransaction.objects.create(
        business_account=ba,
        transaction_type=BusinessTransaction.DEPOSIT,
        amount=Decimal("10000.00"),
        balance_after=Decimal("10000.00"),
    )
    client.force_login(mgr)

    response = client.get(reverse("banking:transactions"))
    transactions = list(response.context["transactions"])

    assert response.status_code == 200
    assert response.context["business_account"] == ba
    assert transactions == [business_txn]
    assert personal_txn not in transactions
    assert b"Acme Corp" in response.content


def test_transaction_history_as_authoriser_shows_business_transactions(client):
    from banking.models import BusinessTransaction

    ba, _, auth_user = make_business_setup()
    personal_txn = deposit(auth_user.account, Decimal("25.00"))
    business_txn = BusinessTransaction.objects.create(
        business_account=ba,
        transaction_type=BusinessTransaction.BILL_PAYMENT,
        amount=Decimal("200.00"),
        balance_after=Decimal("9800.00"),
        description="utilities (ACC-001)",
    )
    client.force_login(auth_user)

    response = client.get(reverse("banking:transactions"))
    transactions = list(response.context["transactions"])

    assert response.status_code == 200
    assert response.context["business_account"] == ba
    assert transactions == [business_txn]
    assert personal_txn not in transactions
    assert b"utilities (ACC-001)" in response.content


def test_billing_page_as_account_manager_shows_business_bill_form(client):
    ba, mgr, _ = make_business_setup()
    client.force_login(mgr)

    response = client.get(reverse("banking:billing"))

    assert response.status_code == 200
    assert response.context["is_manager"] is True
    assert response.context["business_account"] == ba
    assert "bill_pay_form" in response.context
    assert "add_biller_form" not in response.context
    assert b"Business Billing" in response.content


def test_billing_page_as_authoriser_shows_business_bill_form(client):
    ba, _, auth_user = make_business_setup()
    client.force_login(auth_user)

    response = client.get(reverse("banking:billing"))

    assert response.status_code == 200
    assert response.context["is_authoriser"] is True
    assert response.context["business_account"] == ba
    assert "bill_pay_form" in response.context
    assert "add_biller_form" not in response.context
    assert b"Business Billing" in response.content


def test_billing_history_as_manager_shows_business_bill_payments(client):
    from banking.models import BusinessTransaction

    ba, mgr, _ = make_business_setup()
    payment = BusinessTransaction.objects.create(
        business_account=ba,
        transaction_type=BusinessTransaction.BILL_PAYMENT,
        amount=Decimal("75.00"),
        balance_after=Decimal("9925.00"),
        description="rent (INV-001)",
    )
    BusinessTransaction.objects.create(
        business_account=ba,
        transaction_type=BusinessTransaction.DEPOSIT,
        amount=Decimal("10000.00"),
        balance_after=Decimal("10000.00"),
    )
    client.force_login(mgr)

    response = client.get(reverse("banking:billing_history"))
    payments = list(response.context["payments"])

    assert response.status_code == 200
    assert response.context["business_account"] == ba
    assert payments == [payment]


def test_business_roles_cannot_manage_personal_billers(client):
    ba, mgr, auth_user = make_business_setup()
    client.force_login(mgr)

    add_response = client.post(
        reverse("banking:add_biller"),
        {"name": Biller.ELECTRICITY, "reference": "ACC-001"},
    )

    assert add_response.status_code == 403
    assert not mgr.account.billers.exists()

    biller = _make_biller(auth_user.account)
    client.force_login(auth_user)
    remove_response = client.post(reverse("banking:remove_biller", args=[biller.pk]))

    assert remove_response.status_code == 403
    assert auth_user.account.billers.filter(pk=biller.pk).exists()
    assert ba.manager.user == mgr


# --- US3: Authoriser queue view tests ---

def make_biz_with_pending(withdrawal_amount=Decimal("1000.00")):
    from banking.models import PendingTransaction
    from banking.services import deposit_to_business
    ba, mgr, auth_user = make_business_setup()
    ba.refresh_from_db()
    deposit_to_business(ba, Decimal("8000.00"))
    ba.refresh_from_db()
    pt = PendingTransaction.objects.create(
        business_account=ba,
        transaction_type=PendingTransaction.WITHDRAWAL,
        amount=withdrawal_amount,
    )
    return ba, mgr, auth_user, pt


def test_authoriser_queue_view_lists_pending_transactions(client):
    ba, _, auth_user, pt = make_biz_with_pending()
    client.force_login(auth_user)
    response = client.get(reverse("banking:authoriser_queue"))
    assert response.status_code == 200
    assert pt in response.context["pending_txns"]


def test_authoriser_queue_view_empty_queue_shows_message(client):
    ba, _, auth_user = make_business_setup()
    client.force_login(auth_user)
    response = client.get(reverse("banking:authoriser_queue"))
    assert response.status_code == 200
    assert len(response.context["pending_txns"]) == 0


def test_authoriser_queue_view_non_authoriser_returns_403(client):
    user = create_user("NotAuth", "91234567")
    client.force_login(user)
    response = client.get(reverse("banking:authoriser_queue"))
    assert response.status_code == 403


def test_approve_transaction_view_valid_authoriser_redirects(client):
    from banking.models import PendingTransaction
    ba, _, auth_user, pt = make_biz_with_pending()
    client.force_login(auth_user)
    response = client.post(reverse("banking:approve_transaction", args=[pt.pk]))
    assert response.status_code == 302
    pt.refresh_from_db()
    assert pt.status == PendingTransaction.APPROVED


def test_approve_transaction_view_insufficient_funds_flashes_error(client):
    from banking.models import BusinessAccount, AccountManagerProfile, Authoriser, PendingTransaction
    from django.contrib.auth import get_user_model
    User = get_user_model()
    ba = BusinessAccount.objects.create(company_name="BreakCo", uen="BREAK001", street="1 St", city="SG", postal_code="000001")
    mgr = User.objects.create_user(username="mgr_break", email="mgr_break@test.com", name="Mgr", phone_number="80000003", password="Demo@123")
    auth_user = User.objects.create_user(username="auth_break", email="auth_break@test.com", name="Auth", phone_number="80000004", password="Demo@123")
    AccountManagerProfile.objects.create(user=mgr, business_account=ba)
    Authoriser.objects.create(user=auth_user, business_account=ba)
    pt = PendingTransaction.objects.create(
        business_account=ba, transaction_type=PendingTransaction.WITHDRAWAL, amount=Decimal("9999.00")
    )
    client.force_login(auth_user)
    response = client.post(reverse("banking:approve_transaction", args=[pt.pk]))
    assert response.status_code == 302
    pt.refresh_from_db()
    assert pt.status == PendingTransaction.REJECTED


def test_approve_transaction_view_wrong_authoriser_returns_403(client):
    ba, _, auth_user, pt = make_biz_with_pending()
    wrong_user = create_user("WrongAuth", "91234567")
    client.force_login(wrong_user)
    response = client.post(reverse("banking:approve_transaction", args=[pt.pk]))
    assert response.status_code == 403


def test_reject_transaction_view_valid_authoriser_redirects(client):
    from banking.models import PendingTransaction
    ba, _, auth_user, pt = make_biz_with_pending()
    client.force_login(auth_user)
    response = client.post(reverse("banking:reject_transaction", args=[pt.pk]))
    assert response.status_code == 302
    pt.refresh_from_db()
    assert pt.status == PendingTransaction.REJECTED


def test_reject_transaction_view_wrong_authoriser_returns_403(client):
    ba, _, auth_user, pt = make_biz_with_pending()
    wrong_user = create_user("WrongAuth2", "91234567")
    client.force_login(wrong_user)
    response = client.post(reverse("banking:reject_transaction", args=[pt.pk]))
    assert response.status_code == 403


# --- US4: Authoriser dashboard and direct transaction view tests ---

def test_dashboard_view_as_authoriser_shows_business_account(client):
    ba, _, auth_user = make_business_setup()
    client.force_login(auth_user)
    response = client.get(reverse("banking:dashboard"))
    assert response.status_code == 200
    assert response.context["is_authoriser"] is True
    assert response.context["business_account"] == ba


def test_deposit_view_as_authoriser_updates_balance_immediately(client):
    from banking.models import BusinessTransaction
    ba, _, auth_user = make_business_setup()
    client.force_login(auth_user)
    response = client.post(reverse("banking:deposit"), {"amount": "1000.00"})
    ba.refresh_from_db()
    assert response.status_code == 302
    assert ba.balance == Decimal("1000.00")
    assert BusinessTransaction.objects.filter(
        business_account=ba, transaction_type=BusinessTransaction.DEPOSIT
    ).exists()


def test_withdraw_view_as_authoriser_deducts_balance_immediately_no_pending_tx_created(client):
    from banking.models import PendingTransaction
    from banking.services import deposit_to_business
    ba, _, auth_user = make_business_setup()
    deposit_to_business(ba, Decimal("10000.00"))
    ba.refresh_from_db()
    client.force_login(auth_user)
    response = client.post(reverse("banking:withdraw"), {"amount": "2000.00"})
    ba.refresh_from_db()
    assert response.status_code == 302
    assert ba.balance == Decimal("8000.00")
    assert PendingTransaction.objects.filter(business_account=ba).count() == 0


def test_withdraw_view_as_authoriser_floor_breach_shows_error(client):
    from banking.services import deposit_to_business
    ba, _, auth_user = make_business_setup()
    deposit_to_business(ba, Decimal("10000.00"))
    ba.refresh_from_db()
    client.force_login(auth_user)
    response = client.post(reverse("banking:withdraw"), {"amount": "4000.00"})
    ba.refresh_from_db()
    assert response.status_code == 200
    assert b"minimum" in response.content
    assert ba.balance == Decimal("10000.00")


def test_transfer_view_as_authoriser_executes_immediately(client):
    from banking.models import PendingTransaction
    from banking.services import deposit_to_business
    ba, _, auth_user = make_business_setup()
    deposit_to_business(ba, Decimal("10000.00"))
    ba.refresh_from_db()
    recipient = create_user("AuthRecipient", "91234567")
    client.force_login(auth_user)
    response = client.post(
        reverse("banking:transfer"), {"recipient_phone": "91234567", "amount": "500.00"}
    )
    ba.refresh_from_db()
    recipient.account.refresh_from_db()
    assert response.status_code == 302
    assert ba.balance == Decimal("9500.00")
    assert recipient.account.balance == Decimal("500.00")
    assert PendingTransaction.objects.filter(business_account=ba).count() == 0


def test_pay_bill_view_as_authoriser_executes_immediately(client):
    from banking.models import PendingTransaction, BusinessTransaction
    from banking.services import deposit_to_business
    ba, _, auth_user = make_business_setup()
    deposit_to_business(ba, Decimal("10000.00"))
    ba.refresh_from_db()
    client.force_login(auth_user)
    response = client.post(
        reverse("banking:pay_bill"),
        {"category": "utilities", "reference": "ACC-001", "amount": "200.00"},
    )
    ba.refresh_from_db()
    assert response.status_code == 302
    assert ba.balance == Decimal("9800.00")
    assert BusinessTransaction.objects.filter(
        business_account=ba, transaction_type=BusinessTransaction.BILL_PAYMENT
    ).exists()
    assert PendingTransaction.objects.filter(business_account=ba).count() == 0


# --- US5: Manager read-only pending queue view tests ---

def _make_pending_for_manager():
    from banking.models import PendingTransaction
    from banking.services import deposit_to_business
    ba, mgr, auth_user = make_business_setup()
    deposit_to_business(ba, Decimal("5000.00"))
    ba.refresh_from_db()
    pt = PendingTransaction.objects.create(
        business_account=ba,
        transaction_type=PendingTransaction.WITHDRAWAL,
        amount=Decimal("1000.00"),
    )
    return ba, mgr, auth_user, pt


def test_manager_pending_view_lists_pending_transactions(client):
    ba, mgr, _, pt = _make_pending_for_manager()
    client.force_login(mgr)
    response = client.get(reverse("banking:manager_pending"))
    assert response.status_code == 200
    assert pt in response.context["pending_txns"]


def test_manager_pending_view_has_no_approve_reject_controls(client):
    _, mgr, _, _ = _make_pending_for_manager()
    client.force_login(mgr)
    response = client.get(reverse("banking:manager_pending"))
    assert response.status_code == 200
    assert b"Approve" not in response.content
    assert b"Reject" not in response.content


def test_manager_pending_view_empty_queue_shows_message(client):
    ba, mgr, _ = make_business_setup()
    client.force_login(mgr)
    response = client.get(reverse("banking:manager_pending"))
    assert response.status_code == 200
    assert len(response.context["pending_txns"]) == 0


def test_manager_pending_view_non_manager_returns_403(client):
    user = create_user("NotManager", "91234567")
    client.force_login(user)
    response = client.get(reverse("banking:manager_pending"))
    assert response.status_code == 403


def test_manager_pending_view_unauthenticated_redirects_to_login(client):
    response = client.get(reverse("banking:manager_pending"))
    assert response.status_code == 302
    assert reverse("accounts:login") in response.url
