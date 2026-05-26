# Data Model: Banking MCP Server

## No new Django models

The MCP server creates **no new database models**. It reads from and writes to the
existing banking app models via the service layer.

---

## Existing models used

| Model | Used by |
|---|---|
| `accounts.CustomUser` | Login auth, username lookup, create_personal_account |
| `banking.Account` | get_account, deposit_funds, withdraw_funds, transfer_funds, create_personal_account |
| `banking.BusinessAccount` | get_business_account, list_business_transactions, create_business_account |
| `banking.Transaction` | list_transactions |
| `banking.BusinessTransaction` | list_business_transactions, create_business_account (initial deposit record) |
| `banking.Biller` | list_billers, pay_bill, add_biller |
| `banking.AccountManagerProfile` | create_business_account (manager user) |
| `banking.Authoriser` | approve_transaction / reject_transaction auth check, create_business_account (authoriser user) |
| `banking.PendingTransaction` | list_pending_transactions, approve_transaction, reject_transaction |

**Note on `Biller.name` field**: The Django model stores the biller category in a field
named `name` (not `category`), using string choices like `ELECTRICITY`, `WATER_UTILITIES`,
etc. The MCP layer uses `category` as the external name and maps it to `Biller.name`
internally. `b.get_name_display()` returns the human-readable label.

---

## In-memory session token record

Not persisted to the database. Lives in the server process only.

```
TokenRecord
├── username: str          # the authenticated user's username
├── issued_at: datetime    # when the token was created
└── last_used: datetime    # updated on every successful write tool call
```

**Expiry**: Token is invalid when `now() - last_used > MCP_SESSION_TIMEOUT_MINUTES` (default 15 min).

**Storage**: `dict[str, TokenRecord]` keyed by a randomly generated 32-byte hex token string.

---

## Amount validation rules (FR-013)

Applied by the MCP server layer before delegating to `banking.services`:

- `amount > 0`
- `amount == amount.quantize(Decimal("0.01"))` (at most two decimal places)

The existing `banking.services._validate_amount` checks positivity only; the additional
decimal-places check lives in `mcp_server/auth.py` or a shared `mcp_server/utils.py`.

---

## State transitions

### PendingTransaction status flow (unchanged from existing model)

```
PENDING → APPROVED  (approve_transaction tool)
PENDING → REJECTED  (reject_transaction tool)
```

Calling approve/reject on a non-PENDING transaction returns an error; no status change occurs.

---

## Session token lifecycle

```
(no token)
    │  login(username, password) succeeds
    ▼
VALID token
    │  write tool call uses token within 15 min of last use → last_used refreshed
    │  write tool call uses token > 15 min after last use
    ▼
EXPIRED (rejected, "please re-login" message returned)
```
