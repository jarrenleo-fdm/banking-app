# Quickstart: MCP API Key Authentication

## Prerequisites

- Python 3.11+
- Project dependencies installed from `requirements.txt` and `requirements-dev.txt`
- Local `.env` configured as in the existing app quickstarts
- Database migrated

```bash
python manage.py migrate
```

## 1. Run the focused tests

Write failing tests first, then implement until these pass:

```bash
pytest accounts/tests/test_api_keys_models.py accounts/tests/test_api_keys_forms.py accounts/tests/test_api_keys_views.py -v
pytest mcp_server/tests/test_api_key_auth.py mcp_server/tests/test_auth.py -v
```

## 2. Create an API key through the web app

Start the Django server:

```bash
python manage.py runserver
```

Sign in with a personal user, business manager, or business authoriser account. Navigate
to:

```text
/accounts/api-keys/
```

Create a named key and enter the current account password when prompted. Copy the full
secret from the one-time display. After leaving that page, only key metadata should remain
visible.

## 3. Authenticate an MCP client with the key

Run the MCP server:

```bash
python -m mcp_server
```

Call the new MCP tool:

```json
{
  "tool": "login_with_api_key",
  "arguments": {
    "api_key": "<one-time key secret>"
  }
}
```

Expected success shape:

```json
{
  "session_token": "<token>",
  "expires_in_minutes": 15,
  "username": "alice",
  "auth_method": "api_key",
  "api_key_identifier": "ak_2f4c9a1b"
}
```

Use the returned `session_token` with existing protected MCP tools such as
`deposit_funds`, `transfer_funds`, `pay_bill`, `add_biller`, `approve_transaction`, or
`reject_transaction`.

## 4. Revoke and verify

Return to:

```text
/accounts/api-keys/
```

Revoke the key. Then verify:

- `login_with_api_key` with that secret returns `{"error": "Authentication failed."}`.
- Protected MCP actions using a session that came from the revoked key return
  `{"error": "Session expired or invalid. Please log in again."}`.
- Other active keys for the same user still work.

## 5. Run broader validation

```bash
pytest accounts/tests/ mcp_server/tests/ -v
python manage.py check
pre-commit run --all-files
```

## Environment variables

| Variable | Default | Purpose |
|---|---|---|
| `MCP_SESSION_TIMEOUT_MINUTES` | `15` | Idle expiry for MCP session tokens |

No new runtime dependency is required for this feature.
