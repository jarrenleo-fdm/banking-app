# Data Model: Personal Banking MCP Server

## Model Strategy

The 006 MCP feature creates no new Django database models. It consumes existing account,
API-key, personal banking, transaction, and biller models. The only new state owned by this
feature is the in-memory MCP session token record.

## Existing Models Used

| Model | Purpose in 006 MCP |
|---|---|
| `accounts.CustomUser` | Owns the personal account, API keys, phone number, email, username, and password used for signup validation. |
| `accounts.AccountAPIKey` | Backing credential for `login_with_api_key` and active-session revocation checks. |
| `accounts.APIKeyAuditEvent` | Non-sensitive audit trail for API key creation, successful auth, failed auth, and revocation from the 007 feature. |
| `banking.Account` | Personal account balance and relationship to `CustomUser`; target for protected personal tools. |
| `banking.Transaction` | Immutable personal transaction history for deposits, withdrawals, transfers, and bill payments. |
| `banking.Biller` | Saved personal billers with fixed category choices and mandatory reference. |

## Entities

### User

- **Source**: `accounts.CustomUser`
- **Key fields used**: `username`, `name`, `email`, `phone_number`, password hash
- **Relationships**: Owns one personal `banking.Account`; owns zero or more
  `accounts.AccountAPIKey` records.
- **Validation**:
  - Username, email, and phone number must be unique.
  - Phone number is an 8-digit Singapore-style mobile number beginning with `8` or `9`.
  - Password must satisfy the existing password complexity rules.

### Account API Key

- **Source**: `accounts.AccountAPIKey`
- **Key fields used**: owner user, non-secret identifier, secret hash, name, revoked date,
  last-used date.
- **Relationships**: Belongs to exactly one `accounts.CustomUser`.
- **Validation**:
  - Only active, non-revoked keys may authenticate MCP sessions.
  - Raw key secrets are not stored and are not returned by 006 MCP tools.

### Authenticated MCP Session

- **Source**: In-memory `mcp_server.auth.TokenStore`
- **Fields**:
  - `token`: generated 32-byte hex string returned to the MCP client.
  - `username`: owning user identity.
  - `auth_method`: fixed to `api_key`.
  - `api_key_identifier`: non-secret identifier of the key used to create the session.
  - `last_used`: timestamp refreshed on successful validation.
- **Validation**:
  - Missing, unknown, or expired tokens are invalid.
  - Tokens whose backing API key has been revoked are invalid.
  - Session validation returns only the authenticated username to tool handlers.

### Personal Account

- **Source**: `banking.Account`
- **Key fields used**: owner user, balance, created date.
- **Relationships**: Belongs to exactly one `accounts.CustomUser`; owns transactions and
  billers.
- **Validation**:
  - Balance must never become negative.
  - Protected tools must derive the account from the authenticated session.

### Transaction

- **Source**: `banking.Transaction`
- **Key fields used**: transaction ID, account, type, amount, balance after transaction,
  counterparty, description, timestamp.
- **Relationships**: Belongs to one personal account; transfer entries may reference a
  counterparty personal account.
- **Validation**:
  - Immutable history entries are created by existing banking services.
  - MCP serialization returns `Decimal` amounts as strings.

### Biller

- **Source**: `banking.Biller`
- **Key fields used**: account, `name` as category, reference, created date.
- **Relationships**: Belongs to one personal account.
- **Validation**:
  - Category must be one of `ELECTRICITY`, `WATER_UTILITIES`,
    `INTERNET_BROADBAND`, `TELECOMMUNICATIONS`, or `TOWN_COUNCIL`.
  - Reference is mandatory.
  - The tuple `(account, name, reference)` must be unique.

## State Transitions

### API-Key-Backed Session

```text
no session
  -> login_with_api_key(valid active key)
VALID session
  -> protected tool validates within timeout and key still active
VALID session with refreshed last_used
  -> token expires OR backing key is revoked OR token is unknown
INVALID session
```

### Personal Money Movement

```text
requested
  -> authenticate session
  -> validate amount and input
  -> delegate to banking service inside existing transaction boundary
  -> success: balance changes and Transaction is recorded
  -> failure: no balance, biller, or transaction state changes
```

### Personal Signup

```text
submitted signup data
  -> validate identity fields, phone, password, and initial balance
  -> create CustomUser
  -> account signal creates Account
  -> apply optional initial balance when valid
  -> return created account summary without API key material
```
