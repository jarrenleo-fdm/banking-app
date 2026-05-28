# Data Model: MCP API Key Authentication

## New Django models

### AccountAPIKey

Represents one user-owned API key for MCP authentication. The raw secret is never stored.

| Field | Type | Required | Notes |
|---|---|---|---|
| `user` | ForeignKey to `accounts.CustomUser` | yes | Owner; keys cannot be reassigned |
| `name` | string, max 80 | yes | User-visible label for the MCP client or purpose |
| `identifier` | string, unique | yes | Non-secret public identifier shown in lists and audits |
| `secret_hash` | string | yes | Hash of the secret material; raw key is shown once only |
| `created_at` | datetime | yes | Set when the key is created |
| `last_used_at` | datetime, nullable | no | Updated after successful API key authentication |
| `revoked_at` | datetime, nullable | no | Null means active; non-null means revoked |

**Validation rules**

- `name` must not be blank after trimming.
- One user may have at most 5 active keys.
- One user may not have two active keys with the same case-insensitive name.
- `identifier` must be unique and safe to display.
- `secret_hash` must never be blank.
- A revoked key cannot become active again.

**Derived properties**

- `is_active`: true when `revoked_at` is null.
- `display_label`: key name plus short identifier for UI and audit messages.

**State transitions**

```text
CREATED / ACTIVE
    │ revoke
    ▼
REVOKED
```

Revoked keys remain visible as metadata for recognition and audit, but they cannot be used
for future MCP authentication.

---

### APIKeyAuditEvent

Records non-sensitive API key security events.

| Field | Type | Required | Notes |
|---|---|---|---|
| `user` | ForeignKey to `accounts.CustomUser`, nullable | no | Known owner or actor when available |
| `api_key` | ForeignKey to `AccountAPIKey`, nullable | no | Null for malformed or unknown-key failures |
| `action` | choice string | yes | `CREATED`, `AUTH_SUCCESS`, `AUTH_FAILURE`, `REVOKED` |
| `outcome` | choice string | yes | `SUCCESS` or `FAILURE` |
| `reason` | string, max 80, blank | no | Safe category such as `invalid`, `revoked`, `malformed`, `limit_reached` |
| `created_at` | datetime | yes | Event timestamp |

**Validation rules**

- Audit events must not contain raw API key secrets.
- Failure events for unknown or malformed keys must not require a `user` or `api_key`.
- Events are append-only from normal application flows.

---

## Updated in-memory MCP session record

The existing MCP session token store remains process-local, but token records gain
authentication context.

```text
TokenRecord
├── username: str
├── auth_method: "password" | "api_key"
├── api_key_identifier: str | None
└── last_used: datetime
```

**Validation rules**

- Password-authenticated tokens keep current idle-expiry behavior.
- API-key-authenticated tokens keep idle-expiry behavior and must also confirm that the
  referenced API key is still active before a protected write action proceeds.
- If the referenced key is revoked, validation fails with the same generic session error
  used for invalid or expired tokens.

---

## Existing models used

| Model | Usage |
|---|---|
| `accounts.CustomUser` | Owns API keys; password confirmation; MCP user identity |
| `banking.Account` | Existing personal-account authorisation remains username-based |
| `banking.AccountManagerProfile` | Existing business manager role inherited by API-key sessions |
| `banking.Authoriser` | Existing business authoriser role inherited by API-key sessions |
| `banking.Transaction` / `banking.BusinessTransaction` | Unchanged immutable money history for protected operations that are authenticated with an API-key-backed session |

## Secret lifecycle

```text
create_key(user, name)
    │
    ├─ generate raw secret
    ├─ store identifier + secret_hash + metadata
    ├─ record CREATED audit event
    └─ return raw secret for one-time display

later list/review
    └─ show name, identifier, status, created_at, last_used_at, revoked_at

login_with_api_key(raw_secret)
    │
    ├─ find candidate by identifier
    ├─ compare submitted secret with stored hash
    ├─ update last_used_at on success
    ├─ record AUTH_SUCCESS or AUTH_FAILURE audit event
    └─ issue MCP session token on success

revoke_key(identifier)
    │
    ├─ set revoked_at
    └─ record REVOKED audit event
```
