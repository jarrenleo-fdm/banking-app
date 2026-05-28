"""Form tests for MCP API key management."""
import pytest
from django.contrib.auth import get_user_model


User = get_user_model()


def create_user(**overrides):
    data = {
        "username": "Alice",
        "email": "alice@example.com",
        "name": "Alice Example",
        "phone_number": "81234567",
        "password": "StrongerPass123!",
    }
    data.update(overrides)
    return User.objects.create_user(**data)


@pytest.mark.django_db
def test_api_key_create_form_accepts_valid_name_and_password():
    from accounts.forms import APIKeyCreateForm

    user = create_user()
    form = APIKeyCreateForm(
        user=user,
        data={"name": "Claude Desktop", "password": "StrongerPass123!"},
    )

    assert form.is_valid()
    assert form.cleaned_data["name"] == "Claude Desktop"


@pytest.mark.django_db
def test_api_key_create_form_rejects_blank_name():
    from accounts.forms import APIKeyCreateForm

    user = create_user()
    form = APIKeyCreateForm(
        user=user,
        data={"name": "   ", "password": "StrongerPass123!"},
    )

    assert not form.is_valid()
    assert "name" in form.errors


@pytest.mark.django_db
def test_api_key_create_form_rejects_wrong_password():
    from accounts.forms import APIKeyCreateForm

    user = create_user()
    form = APIKeyCreateForm(
        user=user,
        data={"name": "Claude Desktop", "password": "wrong-password"},
    )

    assert not form.is_valid()
    assert "password" in form.errors


@pytest.mark.django_db
def test_api_key_create_form_rejects_duplicate_active_name():
    from accounts.forms import APIKeyCreateForm
    from accounts.models import AccountAPIKey

    user = create_user()
    AccountAPIKey.objects.create(
        user=user,
        name="Claude Desktop",
        identifier="ak_1111111111111111",
        secret_hash="hashed-secret",
    )

    form = APIKeyCreateForm(
        user=user,
        data={"name": "claude desktop", "password": "StrongerPass123!"},
    )

    assert not form.is_valid()
    assert "name" in form.errors


@pytest.mark.django_db
def test_api_key_create_form_rejects_active_key_limit():
    from accounts.forms import APIKeyCreateForm
    from accounts.models import AccountAPIKey

    user = create_user()
    for index in range(AccountAPIKey.ACTIVE_KEY_LIMIT):
        AccountAPIKey.objects.create(
            user=user,
            name=f"Key {index}",
            identifier=f"ak_111111111111111{index}",
            secret_hash="hashed-secret",
        )

    form = APIKeyCreateForm(
        user=user,
        data={"name": "One Too Many", "password": "StrongerPass123!"},
    )

    assert not form.is_valid()
    assert "__all__" in form.errors
