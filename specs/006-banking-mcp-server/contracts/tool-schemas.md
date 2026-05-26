# MCP Tool Contracts

All tools communicate via MCP JSON-RPC over stdio. On error, every tool returns
a JSON object `{"error": "<human-readable message>"}` instead of the success payload.

---

## Open signup tools (no session_token required)

### `create_personal_account`

Create a new personal bank account. No authentication required.

**Input**

| Field | Type | Required | Description |
|---|---|---|---|
| `name` | string | yes | Full name of the account holder |
| `username` | string | yes | Unique login username |
| `email` | string | yes | Unique email address |
| `phone_number` | string | yes | 8-digit Singapore mobile number starting with 8 or 9 |
| `password` | string | yes | Account password |
| `initial_deposit` | string | no | Starting balance in decimal (default `"0.00"`, minimum `"0.00"`) |

**Success output**

```json
{
  "username": "alice",
  "name": "Alice Tan",
  "balance": "500.00",
  "created_at": "2026-05-26T10:00:00+08:00"
}
```

**Error cases**

| Condition | Message |
|---|---|
| Username already taken | `"Username is already taken."` |
| Email already registered | `"Email is already registered."` |
| Phone number already registered | `"Phone number is already registered."` |
| Negative initial deposit | `"Amount must be greater than zero."` |

---

### `create_business_account`

Create a new business bank account (atomically creates business account + manager user +
authoriser user). No authentication required.

**Input**

| Field | Type | Required | Description |
|---|---|---|---|
| `company_name` | string | yes | Legal business name |
| `uen` | string | yes | Unique Entity Number (any non-empty alphanumeric string) |
| `street` | string | yes | Street address |
| `city` | string | yes | City |
| `postal_code` | string | yes | Postal code |
| `initial_deposit` | string | no | Starting balance (default `"7000.00"`, minimum `"7000.00"`) |

**Success output**

```json
{
  "company_name": "Acme Pte Ltd",
  "uen": "202312345A",
  "balance": "10000.00",
  "manager_username": "manager.acme",
  "manager_password": "Xk9mP2qR",
  "manager_phone": "80000001",
  "authoriser_username": "authoriser.acme",
  "authoriser_password": "Lw3nQ8vZ",
  "authoriser_phone": "80000002"
}
```

**Error cases**

| Condition | Message |
|---|---|
| Initial deposit below 7,000 | `"Initial deposit must be at least 7,000."` |
| UEN already exists | `"A business account with this UEN already exists."` |

---

## Authentication

### `login`

Accepts credentials and returns a short-lived session token. Required before any
write tool.

**Input**

| Field | Type | Required | Description |
|---|---|---|---|
| `username` | string | yes | The user's account username |
| `password` | string | yes | The user's password |

**Success output**

```json
{
  "session_token": "<32-byte hex string>",
  "expires_in_minutes": 15
}
```

**Error cases**

| Condition | Message |
|---|---|
| Username not found | `"Authentication failed."` |
| Wrong password | `"Authentication failed."` |

*(Generic message intentional — do not distinguish username vs password.)*

---

## Read tools (no session_token required)

### `get_account`

**Input**

| Field | Type | Required | Description |
|---|---|---|---|
| `username` | string | yes | Personal account owner's username |

**Success output**

```json
{
  "username": "alice",
  "name": "Alice Tan",
  "balance": "1234.56",
  "created_at": "2025-01-15T08:00:00+08:00"
}
```

---

### `get_business_account`

**Input**

| Field | Type | Required | Description |
|---|---|---|---|
| `identifier` | string | yes | Business UEN **or** company name (case-insensitive) |

**Success output**

```json
{
  "company_name": "Acme Pte Ltd",
  "uen": "202312345A",
  "address": "10 Anson Road, #10-01, Singapore 079903",
  "balance": "50000.00",
  "manager": {
    "username": "manager.acme",
    "name": "Manager (Acme Pte Ltd)"
  },
  "authoriser": {
    "username": "authoriser.acme",
    "name": "Authoriser (Acme Pte Ltd)"
  },
  "created_at": "2025-03-01T09:00:00+08:00"
}
```

---

### `list_transactions`

**Input**

| Field | Type | Required | Description |
|---|---|---|---|
| `username` | string | yes | Personal account owner's username |
| `transaction_type` | string | no | One of: `DEPOSIT`, `WITHDRAWAL`, `TRANSFER_OUT`, `TRANSFER_IN`, `BILL_PAYMENT` |
| `date_from` | string | no | ISO 8601 date, inclusive (`YYYY-MM-DD`) |
| `date_to` | string | no | ISO 8601 date, inclusive (`YYYY-MM-DD`) |
| `limit` | integer | no | Number of results (default 20, max 100) |

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
      "description": "",
      "timestamp": "2025-05-01T14:30:00+08:00"
    }
  ],
  "count": 1
}
```

---

### `list_business_transactions`

**Input**

| Field | Type | Required | Description |
|---|---|---|---|
| `identifier` | string | yes | Business UEN or company name |
| `transaction_type` | string | no | One of: `DEPOSIT`, `WITHDRAWAL`, `TRANSFER_OUT`, `BILL_PAYMENT`, `REJECTED` |
| `date_from` | string | no | ISO 8601 date, inclusive |
| `date_to` | string | no | ISO 8601 date, inclusive |
| `limit` | integer | no | Default 20, max 100 |

**Success output** — same shape as `list_transactions` above, without `counterparty_username`.

---

### `list_billers`

**Input**

| Field | Type | Required | Description |
|---|---|---|---|
| `username` | string | yes | Personal account owner's username |

**Success output**

```json
{
  "billers": [
    {
      "id": 7,
      "category": "ELECTRICITY",
      "category_display": "Electricity",
      "reference": "ACC-123456",
      "created_at": "2025-02-10T10:00:00+08:00"
    }
  ],
  "count": 1
}
```

---

### `list_pending_transactions`

**Input**

| Field | Type | Required | Description |
|---|---|---|---|
| `identifier` | string | yes | Business UEN or company name |

**Success output**

```json
{
  "pending_transactions": [
    {
      "id": 3,
      "transaction_type": "TRANSFER_OUT",
      "amount": "5000.00",
      "counterparty_username": "charlie",
      "description": "",
      "created_at": "2025-05-20T11:00:00+08:00"
    }
  ],
  "count": 1
}
```

---

## Write tools (session_token required)

All write tools include:

| Field | Type | Required | Description |
|---|---|---|---|
| `session_token` | string | yes | Token from `login` |

On token failure: `{"error": "Session expired or invalid. Please log in again."}`
On authorisation failure: `{"error": "Not authorised to perform this action."}`

---

### `deposit_funds`

**Additional input**

| Field | Type | Required | Description |
|---|---|---|---|
| `username` | string | yes | Account to deposit into |
| `amount` | string | yes | Positive decimal, ≤ 2 d.p. (e.g. `"100.00"`) |

**Success output**

```json
{
  "new_balance": "1334.56",
  "transaction_id": 55
}
```

---

### `withdraw_funds`

**Additional input**

| Field | Type | Required | Description |
|---|---|---|---|
| `username` | string | yes | Account to withdraw from (must match session user) |
| `amount` | string | yes | Positive decimal, ≤ 2 d.p. |

**Success output**

```json
{
  "new_balance": "1084.56",
  "transaction_id": 56
}
```

---

### `transfer_funds`

**Additional input**

| Field | Type | Required | Description |
|---|---|---|---|
| `from_username` | string | yes | Sender's username (must match session user) |
| `to_username` | string | yes | Recipient's username |
| `amount` | string | yes | Positive decimal, ≤ 2 d.p. |
| `description` | string | no | Optional memo |

**Success output**

```json
{
  "sender_new_balance": "1034.56",
  "out_transaction_id": 57,
  "in_transaction_id": 58
}
```

---

### `pay_bill`

**Additional input**

| Field | Type | Required | Description |
|---|---|---|---|
| `username` | string | yes | Account owner (must match session user) |
| `biller_id` | integer | yes | Biller ID from `list_billers` |
| `amount` | string | yes | Positive decimal, ≤ 2 d.p. |

**Success output**

```json
{
  "new_balance": "984.56",
  "transaction_id": 59
}
```

**Error cases** (beyond common token/auth errors)

| Condition | Message |
|---|---|
| Biller not found or belongs to another account | `"Biller not found."` |
| Insufficient funds | `"Insufficient funds."` |

---

### `add_biller`

**Additional input**

| Field | Type | Required | Description |
|---|---|---|---|
| `username` | string | yes | Personal account owner (must match session user) |
| `category` | string | yes | One of: `ELECTRICITY`, `WATER_UTILITIES`, `INTERNET_BROADBAND`, `TELECOMMUNICATIONS`, `TOWN_COUNCIL` |
| `reference` | string | yes | Account/reference number with the biller (unique per account + category) |

**Success output**

```json
{
  "id": 7,
  "category": "ELECTRICITY",
  "category_display": "Electricity",
  "reference": "ACC-123456",
  "created_at": "2026-05-26T10:00:00+08:00"
}
```

**Error cases**

| Condition | Message |
|---|---|
| Invalid category value | `"Invalid category. Must be one of: ELECTRICITY, WATER_UTILITIES, INTERNET_BROADBAND, TELECOMMUNICATIONS, TOWN_COUNCIL."` |
| Duplicate category + reference for account | `"A biller with this category and reference already exists."` |

---

### `approve_transaction`

**Additional input**

| Field | Type | Required | Description |
|---|---|---|---|
| `pending_transaction_id` | integer | yes | ID from `list_pending_transactions` |

**Success output**

```json
{
  "status": "APPROVED",
  "business_new_balance": "45000.00"
}
```

**Error cases**

| Condition | Message |
|---|---|
| Transaction not PENDING | `"Transaction is no longer pending."` |
| Session user is not the assigned authoriser | `"Not authorised to perform this action."` |

---

### `reject_transaction`

**Additional input**

| Field | Type | Required | Description |
|---|---|---|---|
| `pending_transaction_id` | integer | yes | ID from `list_pending_transactions` |
| `reason` | string | no | Optional rejection reason |

**Success output**

```json
{
  "status": "REJECTED"
}
```

**Error cases** — same as `approve_transaction`.
