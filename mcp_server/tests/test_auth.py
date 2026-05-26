"""Tests for TokenStore, _mcp_validate_amount, and login tool."""
import datetime
from decimal import Decimal
from unittest.mock import patch

import pytest


# ---------------------------------------------------------------------------
# T004 — TokenStore
# ---------------------------------------------------------------------------


class TestTokenStore:
    def test_issue_token_returns_64_char_hex(self):
        from mcp_server.auth import TokenStore

        ts = TokenStore()
        token = ts.issue_token("alice")
        assert len(token) == 64
        assert all(c in "0123456789abcdef" for c in token)

    def test_validate_token_returns_username(self):
        from mcp_server.auth import TokenStore

        ts = TokenStore()
        token = ts.issue_token("alice")
        assert ts.validate_token(token) == "alice"

    def test_validate_unknown_token_raises(self):
        from mcp_server.auth import SessionExpiredError, TokenStore

        ts = TokenStore()
        with pytest.raises(SessionExpiredError):
            ts.validate_token("0" * 64)

    def test_validate_expired_token_raises(self):
        from mcp_server.auth import SessionExpiredError, TokenStore

        ts = TokenStore()
        token = ts.issue_token("alice")
        future = datetime.datetime.now() + datetime.timedelta(hours=1)
        with patch("mcp_server.auth.datetime") as mock_dt:
            mock_dt.now.return_value = future
            with pytest.raises(SessionExpiredError):
                ts.validate_token(token)

    def test_purge_removes_expired_entries(self):
        from mcp_server.auth import TokenStore

        ts = TokenStore()
        token = ts.issue_token("alice")
        future = datetime.datetime.now() + datetime.timedelta(hours=1)
        with patch("mcp_server.auth.datetime") as mock_dt:
            mock_dt.now.return_value = future
            ts._purge_expired()
        assert token not in ts._tokens


# ---------------------------------------------------------------------------
# T006 — _mcp_validate_amount
# ---------------------------------------------------------------------------


class TestMcpValidateAmount:
    def test_valid_amount(self):
        from mcp_server.utils import _mcp_validate_amount

        assert _mcp_validate_amount("50.00") == Decimal("50.00")

    def test_zero_raises(self):
        from mcp_server.utils import _mcp_validate_amount

        with pytest.raises(ValueError, match="positive"):
            _mcp_validate_amount("0")

    def test_zero_decimal_raises(self):
        from mcp_server.utils import _mcp_validate_amount

        with pytest.raises(ValueError, match="positive"):
            _mcp_validate_amount("0.00")

    def test_negative_raises(self):
        from mcp_server.utils import _mcp_validate_amount

        with pytest.raises(ValueError):
            _mcp_validate_amount("-1.00")

    def test_three_decimal_places_raises(self):
        from mcp_server.utils import _mcp_validate_amount

        with pytest.raises(ValueError, match="decimal"):
            _mcp_validate_amount("10.001")

    def test_non_numeric_raises(self):
        from mcp_server.utils import _mcp_validate_amount

        with pytest.raises(ValueError):
            _mcp_validate_amount("abc")


# ---------------------------------------------------------------------------
# T010 — login tool
# ---------------------------------------------------------------------------


_ALICE_SECRET = "TestPass123!"  # test fixture credential — not a real secret


@pytest.mark.django_db
class TestLoginTool:
    def test_valid_credentials_returns_token(self, db_user):
        from mcp_server.server import login

        result = login("alice", _ALICE_SECRET)
        assert "session_token" in result
        assert len(result["session_token"]) == 64
        assert result["expires_in_minutes"] == 15

    def test_wrong_credentials_returns_error(self, db_user):
        from mcp_server.server import login

        result = login("alice", "not-the-right-one")
        assert result == {"error": "Authentication failed."}
        assert "session_token" not in result

    def test_unknown_user_returns_generic_error(self):
        from mcp_server.server import login

        result = login("nobody", "irrelevant")
        assert result == {"error": "Authentication failed."}
        assert "session_token" not in result
