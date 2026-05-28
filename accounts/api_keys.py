"""Helpers for account-owned MCP API keys."""
import secrets

from django.contrib.auth.hashers import check_password, make_password
from django.db import transaction
from django.utils import timezone

from .models import APIKeyAuditEvent, AccountAPIKey


class APIKeyAuthenticationError(Exception):
    """Submitted API key cannot authenticate a user."""


def _new_identifier():
    """Return a unique, non-secret public API key identifier."""
    while True:
        identifier = f"ak_{secrets.token_hex(8)}"
        if not AccountAPIKey.objects.filter(identifier=identifier).exists():
            return identifier


def _new_raw_secret(identifier):
    return f"{identifier}.{secrets.token_urlsafe(32)}"


def check_key_secret(raw_secret, api_key):
    """Return whether raw_secret matches api_key without exposing stored hashes."""
    return check_password(raw_secret, api_key.secret_hash)


@transaction.atomic
def create_key(user, name):
    """Create an API key and return (record, raw_secret) for one-time display."""
    identifier = _new_identifier()
    raw_secret = _new_raw_secret(identifier)
    api_key = AccountAPIKey.objects.create(
        user=user,
        name=name.strip(),
        identifier=identifier,
        secret_hash=make_password(raw_secret),
    )
    APIKeyAuditEvent.objects.create(
        user=user,
        api_key=api_key,
        action=APIKeyAuditEvent.CREATED,
        outcome=APIKeyAuditEvent.SUCCESS,
        reason="created",
    )
    return api_key, raw_secret


def _audit_failure(api_key=None, user=None, reason="invalid"):
    APIKeyAuditEvent.objects.create(
        user=user,
        api_key=api_key,
        action=APIKeyAuditEvent.AUTH_FAILURE,
        outcome=APIKeyAuditEvent.FAILURE,
        reason=reason,
    )


def verify_key(raw_secret):
    """Return (user, api_key) for a valid raw API key or raise a generic error."""
    submitted = (raw_secret or "").strip()
    if "." not in submitted:
        _audit_failure(reason="malformed")
        raise APIKeyAuthenticationError("Authentication failed.")

    identifier, _secret = submitted.split(".", 1)
    if not identifier.startswith("ak_"):
        _audit_failure(reason="malformed")
        raise APIKeyAuthenticationError("Authentication failed.")

    api_key = AccountAPIKey.objects.select_related("user").filter(
        identifier=identifier
    ).first()
    if api_key is None:
        _audit_failure(reason="invalid")
        raise APIKeyAuthenticationError("Authentication failed.")

    if not api_key.is_active:
        _audit_failure(api_key=api_key, user=api_key.user, reason="revoked")
        raise APIKeyAuthenticationError("Authentication failed.")

    if not check_key_secret(submitted, api_key):
        _audit_failure(api_key=api_key, user=api_key.user, reason="invalid")
        raise APIKeyAuthenticationError("Authentication failed.")

    api_key.last_used_at = timezone.now()
    api_key.save(update_fields=["last_used_at"])
    APIKeyAuditEvent.objects.create(
        user=api_key.user,
        api_key=api_key,
        action=APIKeyAuditEvent.AUTH_SUCCESS,
        outcome=APIKeyAuditEvent.SUCCESS,
        reason="authenticated",
    )
    return api_key.user, api_key


@transaction.atomic
def revoke_key(api_key, actor):
    """Revoke an active API key and record a non-sensitive audit event."""
    if api_key.revoked_at is None:
        api_key.revoked_at = timezone.now()
        api_key.save(update_fields=["revoked_at"])
        APIKeyAuditEvent.objects.create(
            user=actor,
            api_key=api_key,
            action=APIKeyAuditEvent.REVOKED,
            outcome=APIKeyAuditEvent.SUCCESS,
            reason="revoked",
        )
    return api_key
