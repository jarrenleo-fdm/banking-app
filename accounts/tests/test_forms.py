"""Form tests for account profile management."""
from django.contrib.auth import get_user_model

from accounts.forms import UserDetailsForm


User = get_user_model()


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


def form_payload(**overrides):
    data = {
        "name": "Alice Updated",
        "email": "updated@example.com",
        "phone_number": "91234567",
        "username": "changed-login",
    }
    data.update(overrides)
    return data


def test_user_details_form_accepts_valid_update():
    user = create_user()

    form = UserDetailsForm(form_payload(), instance=user)

    assert form.is_valid()
    updated_user = form.save()
    assert updated_user.name == "Alice Updated"
    assert updated_user.email == "updated@example.com"
    assert updated_user.phone_number == "91234567"
    assert updated_user.username == "changed-login"


def test_user_details_form_rejects_blank_name():
    user = create_user()

    form = UserDetailsForm(form_payload(name="   "), instance=user)

    assert not form.is_valid()
    assert "name" in form.errors


def test_user_details_form_rejects_duplicate_email():
    user = create_user()
    create_user(
        username="Bob",
        email="bob@example.com",
        phone_number="91234567",
    )

    form = UserDetailsForm(form_payload(email="BOB@example.com"), instance=user)

    assert not form.is_valid()
    assert "email" in form.errors


def test_user_details_form_allows_unchanged_email_and_phone():
    user = create_user()

    form = UserDetailsForm(
        form_payload(
            username="Alice",
            email="ALICE@example.com",
            phone_number="81234567",
        ),
        instance=user,
    )

    assert form.is_valid()


def test_user_details_form_accepts_valid_username_update():
    user = create_user()

    form = UserDetailsForm(form_payload(username="Alice.New_123"), instance=user)

    assert form.is_valid()
    updated_user = form.save()
    assert updated_user.username == "Alice.New_123"


def test_user_details_form_allows_unchanged_username():
    user = create_user()

    form = UserDetailsForm(form_payload(username="Alice"), instance=user)

    assert form.is_valid()


def test_user_details_form_rejects_duplicate_username_case_insensitive():
    user = create_user()
    create_user(
        username="TakenName",
        email="taken@example.com",
        phone_number="92345678",
    )

    form = UserDetailsForm(form_payload(username="takenname"), instance=user)

    assert not form.is_valid()
    assert "username" in form.errors


def test_user_details_form_rejects_invalid_username():
    user = create_user()

    form = UserDetailsForm(form_payload(username="bad username"), instance=user)

    assert not form.is_valid()
    assert "username" in form.errors


def test_user_details_form_rejects_duplicate_phone():
    user = create_user()
    create_user(
        username="Bob",
        email="bob@example.com",
        phone_number="91234567",
    )

    form = UserDetailsForm(form_payload(phone_number="91234567"), instance=user)

    assert not form.is_valid()
    assert "phone_number" in form.errors


def test_user_details_form_rejects_invalid_phone_number():
    user = create_user()

    form = UserDetailsForm(form_payload(phone_number="12345678"), instance=user)

    assert not form.is_valid()
    assert "phone_number" in form.errors


def test_user_details_form_normalizes_phone_number():
    user = create_user()

    form = UserDetailsForm(form_payload(phone_number="9123-4567"), instance=user)

    assert form.is_valid()
    assert form.cleaned_data["phone_number"] == "91234567"
