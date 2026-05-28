"""Tests for API-key-backed TokenStore and MCP amount validation."""
import datetime
from decimal import Decimal
from unittest.mock import patch

import pytest


class TestTokenStore:
    def test_issue_token_returns_64_char_hex(self):
        from mcp_server.auth import TokenStore

        token = TokenStore().issue_token(
            "alice",
            api_key_identifier="ak_1234567890abcdef",
        )
        assert len(token) == 64
        assert all(c in "0123456789abcdef" for c in token)

    def test_issue_token_requires_api_key_identifier(self):
        from mcp_server.auth import TokenStore

        with pytest.raises(ValueError):
            TokenStore().issue_token("alice")

    def test_issue_token_stores_api_key_context(self):
        from mcp_server.auth import TokenStore

        ts = TokenStore()
        token = ts.issue_token(
            "alice",
            api_key_identifier="ak_1234567890abcdef",
        )
        record = ts._tokens[token]
        assert record.username == "alice"
        assert record.auth_method == "api_key"
        assert record.api_key_identifier == "ak_1234567890abcdef"

    @pytest.mark.django_db
    def test_validate_token_returns_username_for_active_key(
        self, db_user, make_api_key
    ):
        from mcp_server.auth import TokenStore

        api_key, _raw_secret = make_api_key(db_user)
        ts = TokenStore()
        token = ts.issue_token(
            "alice",
            api_key_identifier=api_key.identifier,
        )
        assert ts.validate_token(token) == "alice"

    def test_validate_unknown_token_raises(self):
        from mcp_server.auth import SessionExpiredError, TokenStore

        with pytest.raises(SessionExpiredError):
            TokenStore().validate_token("0" * 64)

    def test_validate_missing_token_raises(self):
        from mcp_server.auth import SessionExpiredError, TokenStore

        with pytest.raises(SessionExpiredError):
            TokenStore().validate_token("")

    def test_validate_expired_token_raises(self):
        from mcp_server.auth import SessionExpiredError, TokenStore

        ts = TokenStore()
        token = ts.issue_token(
            "alice",
            api_key_identifier="ak_1234567890abcdef",
        )
        future = datetime.datetime.now() + datetime.timedelta(hours=1)
        with patch("mcp_server.auth.datetime") as mock_dt:
            mock_dt.now.return_value = future
            with pytest.raises(SessionExpiredError):
                ts.validate_token(token)

    def test_purge_removes_expired_entries(self):
        from mcp_server.auth import TokenStore

        ts = TokenStore()
        token = ts.issue_token(
            "alice",
            api_key_identifier="ak_1234567890abcdef",
        )
        future = datetime.datetime.now() + datetime.timedelta(hours=1)
        with patch("mcp_server.auth.datetime") as mock_dt:
            mock_dt.now.return_value = future
            ts._purge_expired()
        assert token not in ts._tokens

    @pytest.mark.django_db
    def test_validate_api_key_token_rejects_revoked_key(self, db_user, make_api_key):
        from accounts.api_keys import revoke_key
        from mcp_server.auth import SessionExpiredError, TokenStore

        api_key, _raw_secret = make_api_key(db_user)
        ts = TokenStore()
        token = ts.issue_token(
            "alice",
            api_key_identifier=api_key.identifier,
        )
        revoke_key(api_key, db_user)

        with pytest.raises(SessionExpiredError):
            ts.validate_token(token)


    def test_revoke_token_removes_it(self):
        from mcp_server.auth import SessionExpiredError, TokenStore

        ts = TokenStore()
        token = ts.issue_token("alice", api_key_identifier="ak_1234567890abcdef")
        assert ts.revoke_token(token) is True
        with pytest.raises(SessionExpiredError):
            ts.validate_token(token)

    def test_revoke_unknown_token_returns_false(self):
        from mcp_server.auth import TokenStore

        assert TokenStore().revoke_token("0" * 64) is False


class TestMcpValidateAmount:
    def test_valid_amount(self):
        from mcp_server.utils import _mcp_validate_amount

        assert _mcp_validate_amount("50.00") == Decimal("50.00")

    def test_zero_raises(self):
        from mcp_server.utils import _mcp_validate_amount

        with pytest.raises(ValueError, match="positive"):
            _mcp_validate_amount("0")

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
