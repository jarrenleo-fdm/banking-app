"""View tests for MCP API key management."""
import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse


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
def test_api_keys_view_requires_authentication(client):
    response = client.get(reverse("accounts:api_keys"), secure=True)

    assert response.status_code == 302
    assert response.url == (
        f"{reverse('accounts:login')}?next={reverse('accounts:api_keys')}"
    )


@pytest.mark.django_db
def test_api_keys_get_shows_create_form_and_metadata_without_secret(client):
    from accounts.api_keys import create_key

    user = create_user()
    key, raw_secret = create_key(user, "Claude Desktop")
    client.force_login(user)

    response = client.get(reverse("accounts:api_keys"), secure=True)

    assert response.status_code == 200
    assert b"Claude Desktop" in response.content
    assert key.identifier.encode() in response.content
    assert raw_secret.encode() not in response.content
    assert b"name=\"name\"" in response.content
    assert b"name=\"password\"" in response.content


@pytest.mark.django_db
def test_api_keys_post_creates_key_and_displays_raw_secret_once(client):
    from accounts.models import AccountAPIKey

    user = create_user()
    client.force_login(user)

    response = client.post(
        reverse("accounts:api_keys"),
        {"name": "Claude Desktop", "password": "StrongerPass123!"},
        secure=True,
    )

    assert response.status_code == 200
    key = AccountAPIKey.objects.get(user=user)
    assert key.name == "Claude Desktop"
    assert key.identifier.encode() in response.content
    assert b"ak_" in response.content
    assert key.secret_hash.encode() not in response.content

    followup = client.get(reverse("accounts:api_keys"), secure=True)
    assert key.identifier.encode() in followup.content
    assert key.secret_hash.encode() not in followup.content


@pytest.mark.django_db
def test_api_keys_post_rejects_duplicate_name_without_creating_key(client):
    from accounts.models import AccountAPIKey

    user = create_user()
    AccountAPIKey.objects.create(
        user=user,
        name="Claude Desktop",
        identifier="ak_1111111111111111",
        secret_hash="hashed-secret",
    )
    client.force_login(user)

    response = client.post(
        reverse("accounts:api_keys"),
        {"name": "claude desktop", "password": "StrongerPass123!"},
        secure=True,
    )

    assert response.status_code == 200
    assert b"errorlist" in response.content
    assert AccountAPIKey.objects.filter(user=user).count() == 1


@pytest.mark.django_db
def test_api_keys_get_shows_status_and_revoked_metadata(client):
    from accounts.api_keys import create_key, revoke_key

    user = create_user()
    active_key, _active_secret = create_key(user, "Claude Desktop")
    revoked_key, _revoked_secret = create_key(user, "Old Client")
    revoke_key(revoked_key, user)
    client.force_login(user)

    response = client.get(reverse("accounts:api_keys"), secure=True)

    assert active_key.identifier.encode() in response.content
    assert revoked_key.identifier.encode() in response.content
    assert b"Active" in response.content
    assert b"Revoked" in response.content
    assert b"Never" in response.content


@pytest.mark.django_db
def test_api_key_revoke_post_revokes_owned_active_key(client):
    from accounts.api_keys import create_key

    user = create_user()
    api_key, raw_secret = create_key(user, "Claude Desktop")
    client.force_login(user)

    response = client.post(
        reverse("accounts:api_key_revoke", args=[api_key.identifier]),
        secure=True,
    )
    api_key.refresh_from_db()

    assert response.status_code == 302
    assert response.url == reverse("accounts:api_keys")
    assert not api_key.is_active
    assert raw_secret.encode() not in response.content


@pytest.mark.django_db
def test_api_key_revoke_post_returns_404_for_other_user_key(client):
    from accounts.api_keys import create_key

    user = create_user()
    other = create_user(
        username="Bob",
        email="bob@example.com",
        phone_number="91234567",
    )
    api_key, _raw_secret = create_key(other, "Other Client")
    client.force_login(user)

    response = client.post(
        reverse("accounts:api_key_revoke", args=[api_key.identifier]),
        secure=True,
    )
    api_key.refresh_from_db()

    assert response.status_code == 404
    assert api_key.is_active


@pytest.mark.django_db
def test_api_key_revoke_post_handles_already_revoked_key(client):
    from accounts.api_keys import create_key, revoke_key

    user = create_user()
    api_key, _raw_secret = create_key(user, "Claude Desktop")
    revoke_key(api_key, user)
    client.force_login(user)

    response = client.post(
        reverse("accounts:api_key_revoke", args=[api_key.identifier]),
        secure=True,
    )

    assert response.status_code == 302
    assert response.url == reverse("accounts:api_keys")


@pytest.mark.django_db
def test_api_key_admin_registration_hides_secret_hash():
    from django.contrib import admin

    from accounts.models import APIKeyAuditEvent, AccountAPIKey

    key_admin = admin.site._registry[AccountAPIKey]
    audit_admin = admin.site._registry[APIKeyAuditEvent]

    assert "secret_hash" not in key_admin.list_display
    assert "secret_hash" in key_admin.exclude
    assert "api_key" in audit_admin.list_display
    assert "reason" in audit_admin.list_display
