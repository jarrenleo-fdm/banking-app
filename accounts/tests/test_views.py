"""Integration tests for authentication views."""
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse


User = get_user_model()


def signup_payload(**overrides):
    data = {
        "username": "Alice",
        "email": "alice@example.com",
        "name": "Alice Example",
        "phone_number": "81234567",
        "password1": "StrongerPass123!",
        "password2": "StrongerPass123!",
    }
    data.update(overrides)
    return data


def create_user(**overrides):
    data = {
        "username": "Alice",
        "email": "alice@example.com",
        "name": "Alice Example",
        "phone_number": "81234567",
        "password": "StrongerPass123",
    }
    data.update(overrides)
    return User.objects.create_user(**data)


def test_get_signup_renders_form(client):
    response = client.get(reverse("accounts:signup"))

    assert response.status_code == 200
    assert b"name=\"username\"" in response.content


def test_post_signup_with_valid_data_creates_user_and_redirects(client):
    response = client.post(reverse("accounts:signup"), signup_payload())

    assert response.status_code == 302
    assert response.url == reverse("accounts:login")
    assert User.objects.filter(username="Alice").exists()


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("username", "alice"),
        ("email", "alice@example.com"),
        ("phone_number", "81234567"),
    ],
)
def test_post_signup_with_duplicate_identity_shows_error(client, field, value):
    create_user()
    payload = signup_payload(
        username="Bob",
        email="bob@example.com",
        phone_number="91234567",
    )
    payload[field] = value

    response = client.post(reverse("accounts:signup"), payload)

    assert response.status_code == 200
    assert b"errorlist" in response.content


def test_post_login_with_valid_credentials_redirects_to_dashboard(client):
    create_user()

    response = client.post(
        reverse("accounts:login"),
        {"username": "alice", "password": "StrongerPass123"},
    )

    assert response.status_code == 302
    assert response.url == reverse("banking:dashboard")


def test_post_login_with_wrong_credentials_shows_generic_error(client):
    create_user()

    response = client.post(
        reverse("accounts:login"),
        {"username": "Alice", "password": "wrong-password"},
    )

    assert response.status_code == 200
    assert b"Invalid username or password." in response.content
    assert b"password is incorrect" not in response.content


def test_post_logout_ends_session(client):
    user = create_user()
    client.force_login(user)

    response = client.post(reverse("accounts:logout"))

    assert response.status_code == 302
    assert response.url == reverse("accounts:login")
    assert "_auth_user_id" not in client.session


def test_unauthenticated_dashboard_access_redirects_to_login(client):
    response = client.get(reverse("banking:dashboard"))

    assert response.status_code == 302
    assert response.url == (
        f"{reverse('accounts:login')}?next={reverse('banking:dashboard')}"
    )


@pytest.mark.parametrize(
    ("password", "expected_fragment"),
    [
        ("strongerpass123!", b"uppercase"),
        ("STRONGERPASS123!", b"lowercase"),
        ("StrongerPass!", b"digit"),
        ("StrongerPass123", b"special"),
    ],
)
def test_signup_rejects_password_missing_character_class(
    client, password, expected_fragment
):
    response = client.post(
        reverse("accounts:signup"),
        signup_payload(password1=password, password2=password),
    )
    assert response.status_code == 200
    assert expected_fragment in response.content


def test_signup_with_initial_balance_creates_account_with_that_balance(client):
    response = client.post(
        reverse("accounts:signup"),
        signup_payload(initial_balance="500.00"),
    )
    assert response.status_code == 302
    user = User.objects.get(username="Alice")
    assert user.account.balance == Decimal("500.00")


def test_signup_with_blank_initial_balance_creates_zero_balance_account(client):
    response = client.post(
        reverse("accounts:signup"),
        signup_payload(initial_balance=""),
    )
    assert response.status_code == 302
    user = User.objects.get(username="Alice")
    assert user.account.balance == Decimal("0.00")


def test_signup_with_negative_initial_balance_is_rejected(client):
    response = client.post(
        reverse("accounts:signup"),
        signup_payload(initial_balance="-100"),
    )
    assert response.status_code == 200
    assert b"errorlist" in response.content
    assert not User.objects.filter(username="Alice").exists()


# --- Business account signup tests (T005 & T006) ---

def business_payload(**overrides):
    data = signup_payload(
        account_type="BUSINESS",
        company_name="Acme Pte Ltd",
        business_registration_number="ABC12345",
    )
    data.update(overrides)
    return data


def test_business_signup_creates_user_business_profile_and_sets_account_type(client):
    from banking.models import Account, BusinessProfile

    response = client.post(reverse("accounts:signup"), business_payload())

    assert response.status_code == 302
    user = User.objects.get(username="Alice")
    assert user.account.account_type == Account.BUSINESS
    assert BusinessProfile.objects.filter(account=user.account).exists()
    profile = user.account.business_profile
    assert profile.company_name == "Acme Pte Ltd"
    assert profile.business_registration_number == "ABC12345"


def test_business_signup_missing_company_name_shows_error(client):
    response = client.post(
        reverse("accounts:signup"),
        business_payload(company_name=""),
    )
    assert response.status_code == 200
    assert b"errorlist" in response.content
    assert not User.objects.filter(username="Alice").exists()


def test_business_signup_missing_registration_number_shows_error(client):
    response = client.post(
        reverse("accounts:signup"),
        business_payload(business_registration_number=""),
    )
    assert response.status_code == 200
    assert b"errorlist" in response.content
    assert not User.objects.filter(username="Alice").exists()


def test_business_signup_invalid_registration_number_format_shows_error(client):
    response = client.post(
        reverse("accounts:signup"),
        business_payload(business_registration_number="AB1"),
    )
    assert response.status_code == 200
    assert b"errorlist" in response.content
    assert not User.objects.filter(username="Alice").exists()


def test_business_signup_duplicate_registration_number_shows_error(client):
    client.post(reverse("accounts:signup"), business_payload())
    payload = business_payload(
        username="Bob",
        email="bob@example.com",
        phone_number="91234567",
        company_name="Beta Corp",
    )
    response = client.post(reverse("accounts:signup"), payload)
    assert response.status_code == 200
    assert b"errorlist" in response.content
    assert not User.objects.filter(username="Bob").exists()


def test_personal_signup_creates_personal_account_without_business_profile(client):
    from banking.models import Account, BusinessProfile

    response = client.post(reverse("accounts:signup"), signup_payload())

    assert response.status_code == 302
    user = User.objects.get(username="Alice")
    assert user.account.account_type == Account.PERSONAL
    assert not BusinessProfile.objects.filter(account=user.account).exists()
