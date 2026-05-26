# Quickstart: Banking MCP Server

## Prerequisites

- Python 3.11+
- The banking app's virtual environment activated
- `db.sqlite3` present at the repo root (run `python manage.py migrate` if missing)

## 1. Install the MCP SDK

```bash
pip install "mcp[cli]>=1.9,<2"
```

Add to `requirements.txt`:

```
mcp[cli]>=1.9,<2
```

## 2. Run the MCP server (stdio)

```bash
python -m mcp_server
```

The server reads from stdin and writes to stdout using the MCP JSON-RPC protocol.
It calls `django.setup()` at startup — no separate Django process is needed.

## 3. Connect from Claude Desktop (example)

Add to `claude_desktop_config.json`:

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

## 4. Run the test suite

```bash
pytest mcp_server/tests/ -v
```

With coverage:

```bash
pytest mcp_server/tests/ --cov=mcp_server --cov-report=term-missing
```

## 5. Environment variables

| Variable | Default | Purpose |
|---|---|---|
| `DJANGO_SETTINGS_MODULE` | `banking_app.settings` | Django settings to load |
| `MCP_SESSION_TIMEOUT_MINUTES` | `15` | Session token idle expiry |

## 6. Typical tool call sequences

### Personal account signup + transfer

```
1. create_personal_account(name="Alice Tan",
                           username="alice",
                           email="alice@example.com",
                           phone_number="81234567",
                           password="...",
                           initial_deposit="500.00") → username, balance, created_at
2. login(username="alice", password="...")           → session_token
3. get_account(username="alice")                     → balance, details  [no token needed]
4. transfer_funds(from_username="alice",
                  to_username="bob",
                  amount="50.00",
                  session_token=<token>)             → new balances
```

### Business account signup

```
1. create_business_account(company_name="Acme Pte Ltd",
                           uen="202312345A",
                           street="10 Anson Road",
                           city="Singapore",
                           postal_code="079903",
                           initial_deposit="10000.00") → credentials (manager + authoriser)
2. login(username=<manager_username>, password=<manager_password>) → session_token
```

### Add a biller + pay a bill

```
1. login(username="alice", password="...")     → session_token
2. add_biller(username="alice",
              category="ELECTRICITY",
              reference="ACC-123456",
              session_token=<token>)           → biller id
3. pay_bill(username="alice",
            biller_id=<id>,
            amount="85.00",
            session_token=<token>)            → new balance
```

Read tools (`get_account`, `list_*`) work without a session token.
Open signup tools (`create_personal_account`, `create_business_account`) require no token.
All other write tools require the token from `login`.
