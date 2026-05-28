"""Model and helper tests for MCP API key authentication."""
import pytest
from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.utils import timezone


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
def test_account_api_key_stores_safe_metadata_only():
    from accounts.models import AccountAPIKey

    user = create_user()
    key = AccountAPIKey.objects.create(
        user=user,
        name="Claude Desktop",
        identifier="ak_1234567890abcdef",
        secret_hash="hashed-secret",
    )

    assert key.user == user
    assert key.name == "Claude Desktop"
    assert key.identifier == "ak_1234567890abcdef"
    assert key.secret_hash == "hashed-secret"
    assert key.last_used_at is None
    assert key.revoked_at is None
    assert key.is_active
    assert "ak_1234567890abcdef" in key.display_label
    assert "hashed-secret" not in str(key)


@pytest.mark.django_db
def test_account_api_key_revoked_state_is_not_active():
    from accounts.models import AccountAPIKey

    user = create_user()
    key = AccountAPIKey.objects.create(
        user=user,
        name="Cursor",
        identifier="ak_abcdef1234567890",
        secret_hash="hashed-secret",
        revoked_at=timezone.now(),
    )

    assert not key.is_active


@pytest.mark.django_db
def test_account_api_key_identifier_is_unique():
    from accounts.models import AccountAPIKey

    user = create_user()
    AccountAPIKey.objects.create(
        user=user,
        name="First",
        identifier="ak_sameidentifier1",
        secret_hash="hashed-secret",
    )

    with pytest.raises(IntegrityError):
        AccountAPIKey.objects.create(
            user=user,
            name="Second",
            identifier="ak_sameidentifier1",
            secret_hash="other-hash",
        )


@pytest.mark.django_db
def test_account_api_key_rejects_duplicate_active_name_per_user():
    from accounts.models import AccountAPIKey

    user = create_user()
    AccountAPIKey.objects.create(
        user=user,
        name="Claude",
        identifier="ak_1111111111111111",
        secret_hash="hashed-secret",
    )

    with pytest.raises(IntegrityError):
        AccountAPIKey.objects.create(
            user=user,
            name="claude",
            identifier="ak_2222222222222222",
            secret_hash="other-hash",
        )


@pytest.mark.django_db
def test_account_api_key_allows_reusing_name_after_revocation():
    from accounts.models import AccountAPIKey

    user = create_user()
    AccountAPIKey.objects.create(
        user=user,
        name="Claude",
        identifier="ak_1111111111111111",
        secret_hash="hashed-secret",
        revoked_at=timezone.now(),
    )

    replacement = AccountAPIKey.objects.create(
        user=user,
        name="claude",
        identifier="ak_2222222222222222",
        secret_hash="other-hash",
    )

    assert replacement.is_active


@pytest.mark.django_db
def test_active_key_count_counts_only_unrevoked_keys():
    from accounts.models import AccountAPIKey

    user = create_user()
    AccountAPIKey.objects.create(
        user=user,
        name="Active",
        identifier="ak_1111111111111111",
        secret_hash="hashed-secret",
    )
    AccountAPIKey.objects.create(
        user=user,
        name="Revoked",
        identifier="ak_2222222222222222",
        secret_hash="other-hash",
        revoked_at=timezone.now(),
    )

    assert AccountAPIKey.active_count_for_user(user) == 1


@pytest.mark.django_db
def test_api_key_audit_event_stores_no_raw_secret():
    from accounts.models import APIKeyAuditEvent, AccountAPIKey

    user = create_user()
    key = AccountAPIKey.objects.create(
        user=user,
        name="Claude",
        identifier="ak_1111111111111111",
        secret_hash="hashed-secret",
    )
    event = APIKeyAuditEvent.objects.create(
        user=user,
        api_key=key,
        action=APIKeyAuditEvent.CREATED,
        outcome=APIKeyAuditEvent.SUCCESS,
        reason="created",
    )

    assert event.user == user
    assert event.api_key == key
    assert event.action == APIKeyAuditEvent.CREATED
    assert event.outcome == APIKeyAuditEvent.SUCCESS
    assert "secret" not in str(event).lower()


@pytest.mark.django_db
def test_create_key_returns_raw_secret_and_stores_only_hash():
    from accounts.api_keys import check_key_secret, create_key
    from accounts.models import APIKeyAuditEvent

    user = create_user()

    key, raw_secret = create_key(user, "Claude Desktop")

    assert raw_secret.startswith(f"{key.identifier}.")
    assert raw_secret not in key.secret_hash
    assert check_key_secret(raw_secret, key)
    assert APIKeyAuditEvent.objects.filter(
        user=user,
        api_key=key,
        action=APIKeyAuditEvent.CREATED,
        outcome=APIKeyAuditEvent.SUCCESS,
    ).exists()


@pytest.mark.django_db
def test_create_key_identifier_uses_safe_prefix():
    from accounts.api_keys import create_key

    user = create_user()

    key, raw_secret = create_key(user, "Cursor")

    assert key.identifier.startswith("ak_")
    assert raw_secret.startswith("ak_")
    assert " " not in raw_secret


@pytest.mark.django_db
def test_revoke_key_marks_key_inactive_and_preserves_other_keys():
    from accounts.api_keys import create_key, revoke_key

    user = create_user()
    first, _first_secret = create_key(user, "Claude")
    second, _second_secret = create_key(user, "Cursor")

    revoke_key(first, user)
    first.refresh_from_db()
    second.refresh_from_db()

    assert not first.is_active
    assert first.revoked_at is not None
    assert second.is_active


@pytest.mark.django_db
def test_revoke_key_allows_replacement_with_same_name():
    from accounts.api_keys import create_key, revoke_key

    user = create_user()
    first, _first_secret = create_key(user, "Claude")
    revoke_key(first, user)

    replacement, _replacement_secret = create_key(user, "claude")

    assert replacement.is_active
    assert replacement.name == "claude"


@pytest.mark.django_db
def test_created_and_revoked_audit_events_never_include_raw_secret():
    from accounts.api_keys import create_key, revoke_key
    from accounts.models import APIKeyAuditEvent

    user = create_user()
    api_key, raw_secret = create_key(user, "Claude")
    revoke_key(api_key, user)

    events = APIKeyAuditEvent.objects.filter(api_key=api_key).order_by("created_at")
    assert [event.action for event in events] == [
        APIKeyAuditEvent.CREATED,
        APIKeyAuditEvent.REVOKED,
    ]
    for event in events:
        assert raw_secret not in str(event)
        assert raw_secret not in event.reason
