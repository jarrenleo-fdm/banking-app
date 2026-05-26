"""Session token store for the MCP server."""
import os
import secrets
from dataclasses import dataclass, field
from datetime import datetime, timedelta


MCP_SESSION_TIMEOUT_MINUTES = int(os.environ.get("MCP_SESSION_TIMEOUT_MINUTES", "15"))


class SessionExpiredError(Exception):
    """Token is missing, expired, or has been purged."""


@dataclass
class _TokenRecord:
    username: str
    last_used: datetime = field(default_factory=datetime.now)


class TokenStore:
    def __init__(self):
        self._tokens: dict[str, _TokenRecord] = {}

    def issue_token(self, username: str) -> str:
        token = secrets.token_hex(32)
        self._tokens[token] = _TokenRecord(username=username)
        return token

    def validate_token(self, token: str) -> str:
        """Return username for valid token; raise SessionExpiredError otherwise."""
        self._purge_expired()
        if token not in self._tokens:
            raise SessionExpiredError("Session expired or invalid. Please log in again.")
        record = self._tokens[token]
        record.last_used = datetime.now()
        return record.username

    def _purge_expired(self) -> None:
        cutoff = datetime.now() - timedelta(minutes=MCP_SESSION_TIMEOUT_MINUTES)
        expired = [t for t, r in self._tokens.items() if r.last_used < cutoff]
        for t in expired:
            del self._tokens[t]


token_store = TokenStore()
