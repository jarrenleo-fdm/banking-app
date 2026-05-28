# Quickstart: Personal Banking MCP Server

## Prerequisites

- Python 3.11+
- The banking app's virtual environment activated
- `db.sqlite3` present at the repo root, or run `python manage.py migrate`
  (`python3 manage.py migrate` on systems without a `python` alias)
- At least one account-owned MCP API key created through `/accounts/api-keys/`

## 1. Install Dependencies

```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

`requirements.txt` must include:

```text
mcp[cli]>=1.9,<2
```

## 2. Run the MCP Server

```bash
python -m mcp_server
# Or, if your shell does not provide a python alias:
python3 -m mcp_server
```

The server uses MCP JSON-RPC over stdio. It configures Django settings at startup; no
separate Django HTTP process is required for MCP tools.

## 3. Connect from an MCP Client

Example Claude Desktop-style configuration:

```json
{
  "mcpServers": {
    "banking": {
      "command": "python",
      "args": ["-m", "mcp_server"],
      "cwd": "/path/to/banking-app"
    }
  }
}
```

Use `"command": "python3"` in MCP clients when that is the available interpreter.

## 4. Authenticate With an API Key

Create an API key in the web app at `/accounts/api-keys/`, then use the one-time raw secret
with MCP:

```text
login_with_api_key(api_key="<raw key shown once>")
  -> session_token, expires_in_minutes, username, auth_method, api_key_identifier
```

Username/password MCP login is not supported.

> **Assistant behaviour note:** When a user asks to log in via MCP, only ask whether they have an
> API key. Do not offer to generate one on their behalf — API keys must be created through the web
> app. If the user has no key, inform them they cannot log in until they create one at
> `/accounts/api-keys/`.

## 5. Typical Tool Call Sequences

### Personal Account Signup

```text
create_personal_account(
    name="Alice Tan",
    username="alice",
    email="alice@example.com",
    phone_number="81234567",
    password="StrongPass123!",
    initial_deposit="500.00"
)
  -> username, name, phone_number, balance, created_at
```

This does not create an API key. The new user must create an API key through the account
API-key feature before using protected MCP tools.

### Check Balance and Transactions

```text
login_with_api_key(api_key="<alice api key>")
  -> session_token

get_account(session_token=<token>)
  -> username, name, phone_number, balance, created_at

list_transactions(session_token=<token>, limit=10)
  -> transactions, count
```

### Transfer by Phone Number

```text
login_with_api_key(api_key="<alice api key>")
  -> session_token

transfer_funds(
    session_token=<token>,
    recipient_phone="91234567",
    amount="50.00",
    description="Lunch split"
)
  -> sender_new_balance, out_transaction_id, in_transaction_id
```

### Add a Biller and Pay It

```text
login_with_api_key(api_key="<alice api key>")
  -> session_token

add_biller(
    session_token=<token>,
    category="ELECTRICITY",
    reference="ACC-123456"
)
  -> id, category, category_display, reference, created_at

pay_bill(
    session_token=<token>,
    biller_id=<id>,
    amount="85.00"
)
  -> new_balance, transaction_id
```

## 6. Run Tests

```bash
pytest mcp_server/tests/ -v
```

With coverage:

```bash
pytest mcp_server/tests/ --cov=mcp_server --cov-report=term-missing
```

Focused checks:

```bash
pytest mcp_server/tests/test_api_key_auth.py mcp_server/tests/test_auth.py -v
pytest mcp_server/tests/test_accounts.py mcp_server/tests/test_transactions.py -v
pytest mcp_server/tests/test_transfers.py mcp_server/tests/test_bills.py -v
pytest mcp_server/tests/test_creation.py -v
```

## 7. Environment Variables

| Variable | Default | Purpose |
|---|---|---|
| `DJANGO_SETTINGS_MODULE` | `banking_app.settings` | Django settings module loaded by MCP process |
| `MCP_SESSION_TIMEOUT_MINUTES` | `15` | API-key-backed session token idle expiry |

## 8. Unsupported Tools

The personal MCP server must not expose:

- username/password MCP `login`
- business account lookup
- business transaction history
- pending transaction listing
- business approval or rejection
- business account creation
