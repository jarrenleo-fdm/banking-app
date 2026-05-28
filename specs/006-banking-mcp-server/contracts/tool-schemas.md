# MCP Tool Contracts: Personal Banking MCP Server

All tools communicate via MCP JSON-RPC over stdio. On error, every tool returns:

```json
{
  "error": "<human-readable message>"
}
```

`Decimal` values are serialized as strings. Raw API key secrets are accepted only by
`login_with_api_key` and are never returned by any tool.

## Common Protected Tool Behavior

All protected tools include:

| Field | Type | Required | Description |
|---|---|---|---|
| `session_token` | string | yes | Short-lived token returned by `login_with_api_key` |

Common protected-tool errors:

| Condition | Message |
|---|---|
| Missing, invalid, expired, or revoked session | `"Session expired or invalid. Please log in again."` |
| Target resource does not belong to session user | `"Not authorised to perform this action."` |

Protected tools derive the acting personal account from `session_token`. They do not accept
a target username or account ID.

---

## Open Tools

### `create_personal_account`

Create a new personal bank account. No session token is required.

**Input**

| Field | Type | Required | Description |
|---|---|---|---|
| `name` | string | yes | Full name of the account holder |
| `username` | string | yes | Unique login username |
| `email` | string | yes | Unique email address |
| `phone_number` | string | yes | 8-digit Singapore mobile number beginning with `8` or `9` |
| `password` | string | yes | Password satisfying account password rules |
| `initial_deposit` | string | no | Starting balance decimal string; defaults to `"0.00"` |

**Success output**

```json
{
  "username": "alice",
  "name": "Alice Tan",
  "phone_number": "81234567",
  "balance": "500.00",
  "created_at": "2026-05-28T10:00:00+08:00"
}
```

**Error cases**

| Condition | Message |
|---|---|
| Username already taken | `"Username is already taken."` |
| Email already registered | `"Email is already registered."` |
| Phone number already registered | `"Phone number is already registered."` |
| Invalid phone number | `"Enter a valid Singapore mobile number."` |
| Weak password | Password validation message from existing password rules |
| Negative initial balance | `"Amount must be greater than or equal to zero."` |
| Non-numeric initial balance | `"Invalid amount."` |
| More than two decimal places | `"Amount must have at most 2 decimal places."` |

**Notes**

- This tool must not create or return an API key.
- After signup, authenticated MCP use requires an API key created through the account
  API-key feature.

---

### `login_with_api_key`

Authenticate an MCP client with a user-owned API key and issue a short-lived session token.

**Input**

| Field | Type | Required | Description |
|---|---|---|---|
| `api_key` | string | yes | Full one-time API key secret previously created by the account user |

**Success output**

```json
{
  "session_token": "<32-byte hex string>",
  "expires_in_minutes": 15,
  "username": "alice",
  "auth_method": "api_key",
  "api_key_identifier": "ak_0123456789abcdef"
}
```

**Error cases**

| Condition | Message |
|---|---|
| Invalid, malformed, expired, or revoked API key | `"Authentication failed."` |

---

## Protected Read Tools

### `get_account`

Return the authenticated user's personal account summary.

**Input**

| Field | Type | Required | Description |
|---|---|---|---|
| `session_token` | string | yes | Token from `login_with_api_key` |

**Success output**

```json
{
  "username": "alice",
  "name": "Alice Tan",
  "phone_number": "81234567",
  "balance": "1234.56",
  "created_at": "2026-05-28T10:00:00+08:00"
}
```

---

### `list_transactions`

Return the authenticated user's personal transaction history.

**Input**

| Field | Type | Required | Description |
|---|---|---|---|
| `session_token` | string | yes | Token from `login_with_api_key` |
| `transaction_type` | string | no | One of `DEPOSIT`, `WITHDRAWAL`, `TRANSFER_OUT`, `TRANSFER_IN`, `BILL_PAYMENT` |
| `date_from` | string | no | Inclusive date filter in `YYYY-MM-DD` format |
| `date_to` | string | no | Inclusive date filter in `YYYY-MM-DD` format |
| `limit` | integer | no | Default 20; maximum 100 |

**Success output**

```json
{
  "transactions": [
    {
      "id": 42,
      "transaction_type": "TRANSFER_OUT",
      "amount": "50.00",
      "balance_after": "1184.56",
      "counterparty_username": "bob",
      "counterparty_phone": "91234567",
      "description": "Lunch split",
      "timestamp": "2026-05-28T14:30:00+08:00"
    }
  ],
  "count": 1
}
```

---

### `list_billers`

Return the authenticated user's saved personal billers.

**Input**

| Field | Type | Required | Description |
|---|---|---|---|
| `session_token` | string | yes | Token from `login_with_api_key` |

**Success output**

```json
{
  "billers": [
    {
      "id": 7,
      "category": "ELECTRICITY",
      "category_display": "Electricity",
      "reference": "ACC-123456",
      "created_at": "2026-05-28T10:00:00+08:00"
    }
  ],
  "count": 1
}
```

---

## Protected Write Tools

### `deposit_funds`

Deposit funds into the authenticated user's personal account.

**Input**

| Field | Type | Required | Description |
|---|---|---|---|
| `session_token` | string | yes | Token from `login_with_api_key` |
| `amount` | string | yes | Positive decimal string with at most two decimal places |

**Success output**

```json
{
  "new_balance": "1334.56",
  "transaction_id": 55
}
```

---

### `withdraw_funds`

Withdraw funds from the authenticated user's personal account.

**Input**

| Field | Type | Required | Description |
|---|---|---|---|
| `session_token` | string | yes | Token from `login_with_api_key` |
| `amount` | string | yes | Positive decimal string with at most two decimal places |

**Success output**

```json
{
  "new_balance": "1084.56",
  "transaction_id": 56
}
```

**Error cases**

| Condition | Message |
|---|---|
| Insufficient funds | `"Insufficient funds."` |

---

### `transfer_funds`

Transfer funds from the authenticated user's personal account to another personal account
identified by phone number.

**Input**

| Field | Type | Required | Description |
|---|---|---|---|
| `session_token` | string | yes | Token from `login_with_api_key` |
| `recipient_phone` | string | yes | Recipient's registered Singapore mobile number |
| `amount` | string | yes | Positive decimal string with at most two decimal places |
| `description` | string | no | Optional transfer description, maximum 200 characters |

**Success output**

```json
{
  "sender_new_balance": "1034.56",
  "out_transaction_id": 57,
  "in_transaction_id": 58
}
```

**Error cases**

| Condition | Message |
|---|---|
| Recipient not found | `"Recipient not found."` |
| Sender is recipient | `"Cannot transfer to your own account."` |
| Insufficient funds | `"Insufficient funds."` |
| Description too long | `"Description must be 200 characters or fewer."` |

---

### `add_biller`

Save a biller for the authenticated user's personal account.

**Input**

| Field | Type | Required | Description |
|---|---|---|---|
| `session_token` | string | yes | Token from `login_with_api_key` |
| `category` | string | yes | One of `ELECTRICITY`, `WATER_UTILITIES`, `INTERNET_BROADBAND`, `TELECOMMUNICATIONS`, `TOWN_COUNCIL` |
| `reference` | string | yes | Mandatory account/reference number, unique per account and category |

**Success output**

```json
{
  "id": 7,
  "category": "ELECTRICITY",
  "category_display": "Electricity",
  "reference": "ACC-123456",
  "created_at": "2026-05-28T10:00:00+08:00"
}
```

**Error cases**

| Condition | Message |
|---|---|
| Invalid category | `"Invalid category. Must be one of: ELECTRICITY, WATER_UTILITIES, INTERNET_BROADBAND, TELECOMMUNICATIONS, TOWN_COUNCIL."` |
| Blank reference | `"Reference is required."` |
| Duplicate category and reference | `"A biller with this category and reference already exists."` |

---

### `pay_bill`

Pay one of the authenticated user's saved billers.

**Input**

| Field | Type | Required | Description |
|---|---|---|---|
| `session_token` | string | yes | Token from `login_with_api_key` |
| `biller_id` | integer | yes | Biller ID returned by `list_billers` or `add_biller` |
| `amount` | string | yes | Positive decimal string with at most two decimal places |

**Success output**

```json
{
  "new_balance": "984.56",
  "transaction_id": 59
}
```

**Error cases**

| Condition | Message |
|---|---|
| Biller not found or belongs to another account | `"Biller not found."` |
| Insufficient funds | `"Insufficient funds."` |

---

## Removed / Unsupported MCP Tools

The following tools are out of scope for this feature and must not be registered:

- `login`
- `get_business_account`
- `list_business_transactions`
- `list_pending_transactions`
- `approve_transaction`
- `reject_transaction`
- `create_business_account`
