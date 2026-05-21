# Banking Endpoint Contracts

Branch: `001-core-banking-operations` | Generated: 2026-05-21

All endpoints require authentication. Unauthenticated requests are redirected to
`/accounts/login/?next=<url>` (FR-007).

All POST endpoints require a valid Django CSRF token (`csrfmiddlewaretoken` form
field).

Monetary amounts are validated as positive decimals with at most 2 decimal
places. All arithmetic uses Python `Decimal`; floating-point types are never
used (FR-026).

---

## GET `/dashboard/`

Displays the user's current balance and recent transactions.

**Auth required**: Yes
**Template**: `banking/dashboard.html`

**Context passed to template**:

| Key | Type | Description |
|-----|------|-------------|
| `account` | Account | The logged-in user's account object |
| `balance` | Decimal | `account.balance` — current balance (FR-008, FR-010) |
| `recent_transactions` | QuerySet | Last 5 Transaction objects for this account, ordered by `-timestamp` |
| `user` | CustomUser | The logged-in user (for displaying name and phone number) |

**Deposit and withdraw forms** are rendered on this page for quick access. Each
submits to its respective endpoint below.

---

## POST `/banking/deposit/`

Credits the logged-in user's account.

**Auth required**: Yes

**Form fields**:

| Field | Type | Validation |
|-------|------|------------|
| `amount` | DecimalField | Required; must be > 0.00 (FR-014) |

**On success** (FR-011):
- `services.deposit(account, amount)` called inside `@transaction.atomic`
- Balance increases by `amount`
- `Transaction(type=DEPOSIT)` record created
- Redirect to `/dashboard/` with flash "Deposited $X successfully."

**On failure**:
- `amount <= 0` → validation error; balance unchanged (FR-014)
- Non-numeric input → validation error

---

## POST `/banking/withdraw/`

Debits the logged-in user's account.

**Auth required**: Yes

**Form fields**:

| Field | Type | Validation |
|-------|------|------------|
| `amount` | DecimalField | Required; must be > 0.00 (FR-014) |

**On success** (FR-012):
- `services.withdraw(account, amount)` called inside `@transaction.atomic`
- Balance decreases by `amount`
- `Transaction(type=WITHDRAWAL)` record created
- Redirect to `/dashboard/` with flash "Withdrew $X successfully."

**On failure**:
- `amount <= 0` → validation error; balance unchanged (FR-014)
- `amount > account.balance` → "Insufficient funds" error; balance unchanged
  (FR-013)

---

## POST `/banking/transfer/`

Moves funds from the logged-in user to another registered user identified by
their phone number.

**Auth required**: Yes

**Form fields**:

| Field | Type | Validation |
|-------|------|------------|
| `recipient_phone` | CharField | Required; must match `^[89]\d{7}$` after normalization |
| `amount` | DecimalField | Required; must be > 0.00 (FR-020) |

**On success** (FR-015, FR-016, FR-021):
- `services.transfer(sender_account, recipient_phone, amount)` called inside a
  single `@transaction.atomic` block
- Sender balance decreases by `amount`; recipient balance increases by `amount`
- Two `Transaction` records created atomically:
  - `Transaction(account=sender, type=TRANSFER_OUT, counterparty=recipient)`
  - `Transaction(account=recipient, type=TRANSFER_IN, counterparty=sender)`
- Redirect to `/dashboard/` with flash "Sent $X to [recipient name]."

**On failure**:
- `amount <= 0` → validation error; no balances change (FR-020)
- `amount > sender.balance` → "Insufficient funds"; no balances change (FR-017)
- `recipient_phone` not registered → "No account found with that phone number";
  no balances change (FR-018)
- `recipient_phone` matches sender's own phone → "Cannot transfer to your own
  account"; no balances change (FR-019)
- Non-numeric or invalid format → validation error

---

## GET `/banking/transactions/`

Displays the logged-in user's full transaction history.

**Auth required**: Yes
**Template**: `banking/transactions.html`

**Context passed to template**:

| Key | Type | Description |
|-----|------|-------------|
| `transactions` | QuerySet | All Transaction objects for this account, ordered by `-timestamp` (FR-024) |
| `account` | Account | The logged-in user's account |

**Per-transaction display** (FR-023):
- `transaction_type` — human-readable label (Deposit / Withdrawal / Transfer
  Out / Transfer In)
- `amount` — formatted decimal
- `timestamp` — date and time
- `balance_after` — balance snapshot after this transaction
- `counterparty` — other party's name and phone (for transfers only; FR-023)

**Access control** (FR-007, FR-024): Each user sees only their own transactions.
The queryset is always filtered by `account__user=request.user`.

**Empty state** (FR-024 acceptance scenario 4): If no transactions exist, render
"You have no transactions yet."
