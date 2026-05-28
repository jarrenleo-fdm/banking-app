"""Session token store for the MCP server."""
import os
import secrets
from dataclasses import dataclass, field
from datetime import datetime, timedelta


MCP_SESSION_TIMEOUT_MINUTES = int(os.environ.get("MCP_SESSION_TIMEOUT_MINUTES", "15"))
SESSION_INVALID_MESSAGE = "Session expired or invalid. Please log in again."


class SessionExpiredError(Exception):
    """Token is missing, expired, or has been purged."""


@dataclass
class _TokenRecord:
    username: str
    api_key_identifier: str
    auth_method: str = "api_key"
    last_used: datetime = field(default_factory=datetime.now)


class TokenStore:
    def __init__(self):
        self._tokens: dict[str, _TokenRecord] = {}

    def issue_token(self, username: str, api_key_identifier: str | None = None) -> str:
        if not api_key_identifier:
            raise ValueError("API key identifier is required.")
        token = secrets.token_hex(32)
        self._tokens[token] = _TokenRecord(
            username=username,
            api_key_identifier=api_key_identifier,
        )
        return token

    def revoke_token(self, token: str) -> bool:
        """Remove a token from the store. Returns True if it existed."""
        return self._tokens.pop(token, None) is not None

    def validate_token(self, token: str) -> str:
        """Return username for valid token; raise SessionExpiredError otherwise."""
        self._purge_expired()
        if token not in self._tokens:
            raise SessionExpiredError(SESSION_INVALID_MESSAGE)
        record = self._tokens[token]
        if not self._api_key_is_active(record.api_key_identifier):
            del self._tokens[token]
            raise SessionExpiredError(SESSION_INVALID_MESSAGE)
        record.last_used = datetime.now()
        return record.username

    def _purge_expired(self) -> None:
        cutoff = datetime.now() - timedelta(minutes=MCP_SESSION_TIMEOUT_MINUTES)
        expired = [t for t, r in self._tokens.items() if r.last_used < cutoff]
        for t in expired:
            del self._tokens[t]

    def _api_key_is_active(self, identifier: str | None) -> bool:
        if not identifier:
            return False
        try:
            from accounts.models import AccountAPIKey
        except ImportError:
            return False
        return AccountAPIKey.objects.filter(
            identifier=identifier,
            revoked_at__isnull=True,
        ).exists()


token_store = TokenStore()
