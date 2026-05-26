# Data Model: Business Account (Revised Model)

## Summary

One migration (`0009`) makes all schema changes: adds three new models (`BusinessAccount`,
`AccountManagerProfile`, `BusinessTransaction`), modifies two existing models (`Authoriser`,
`PendingTransaction`), and removes two stale models (`BusinessProfile`, `account_type` on `Account`).
Personal account infrastructure (`Account`, `Transaction`, `Biller`) is unchanged.

---

## Entities

### BusinessAccount — NEW

Standalone banking entity representing the business. Not a login account.

| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| `id` | BigAutoField PK | | |
| `company_name` | CharField(200) | NOT NULL | |
| `uen` | CharField(50) | NOT NULL, UNIQUE | Any non-empty alphanumeric string |
| `street` | CharField(200) | NOT NULL | |
| `city` | CharField(100) | NOT NULL | |
| `postal_code` | CharField(20) | NOT NULL | |
| `balance` | DecimalField(12,2) | NOT NULL, default 0.00 | Fixed-precision, never float |
| `created_at` | DateTimeField | auto_now_add | |

**Relationships**:
- `manager` → `AccountManagerProfile` (OneToOne, reverse)
- `authoriser` → `Authoriser` (OneToOne, reverse)
- `pending_transactions` → `PendingTransaction` (ForeignKey, reverse)
- `transactions` → `BusinessTransaction` (ForeignKey, reverse)

**Validation rules**:
- `company_name`, `uen`, `street`, `city`, `postal_code` must not be blank or whitespace-only
- `uen` must be unique across all `BusinessAccount` records
- `balance` must be ≥ 7,000.00 at all times (enforced at creation, at outgoing-transaction submission, and at authoriser approval)
- `balance` is set to `initial_deposit` (≥ 7,000.00) at creation; initial deposit is recorded as a `BusinessTransaction(DEPOSIT)` in the same `@transaction.atomic` block

---

### AccountManagerProfile — NEW

Links a `CustomUser` 1:1 to a `BusinessAccount`. Created by mock SQL during business account creation.

| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| `id` | BigAutoField PK | | |
| `user` | OneToOneField → CustomUser | CASCADE, related_name=`manager_profile` | |
| `business_account` | OneToOneField → BusinessAccount | CASCADE, related_name=`manager` | |

**Invariants**:
- Exactly one `AccountManagerProfile` exists per `BusinessAccount`
- The linked `CustomUser` was auto-created by mock SQL; its `Account` (personal) has zero balance and is not used by the manager flow

---

### Authoriser — MODIFIED

Previously FKed to `Account` (many per account); now OneToOne to `BusinessAccount`.
`assigned_by` field removed (auto-creation makes it irrelevant).

| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| `id` | BigAutoField PK | | |
| `business_account` | OneToOneField → BusinessAccount | CASCADE, related_name=`authoriser` | Changed from ForeignKey → Account |
| `user` | OneToOneField → CustomUser | PROTECT, related_name=`authoriser_profile` | Changed from ForeignKey |
| `assigned_at` | DateTimeField | auto_now_add | |

**Removed fields**: `assigned_by` (was FK to CustomUser — no longer meaningful)
**Removed constraint**: `unique_together` (superseded by OneToOneField)

**Invariants**:
- Exactly one `Authoriser` per `BusinessAccount`
- A `CustomUser` can be authoriser for at most one `BusinessAccount`

---

### PendingTransaction — MODIFIED

Previously FKed to `Account`; now FKed to `BusinessAccount`. `biller` FK removed (business bill payments don't use saved billers).

| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| `id` | BigAutoField PK | | |
| `business_account` | ForeignKey → BusinessAccount | PROTECT, related_name=`pending_transactions` | Renamed from `account`; FK target changed |
| `transaction_type` | CharField(20) | choices: WITHDRAWAL, TRANSFER_OUT, BILL_PAYMENT | Outgoing only |
| `amount` | DecimalField(12,2) | NOT NULL | |
| `counterparty` | ForeignKey → Account | SET_NULL, null/blank | For TRANSFER_OUT: recipient personal account |
| `description` | CharField(200) | blank | Bill payment: "Category (reference)" |
| `status` | CharField(10) | choices: PENDING/APPROVED/REJECTED/CANCELLED, default PENDING | |
| `created_at` | DateTimeField | auto_now_add | |
| `decided_at` | DateTimeField | null/blank | Set on approve/reject |
| `decided_by` | ForeignKey → CustomUser | SET_NULL, null/blank | The authoriser who acted |

**Removed field**: `biller` FK (was FK to Biller)

**State transitions**:
```
PENDING → APPROVED  (authoriser approves → execute → create BusinessTransaction)
PENDING → REJECTED  (authoriser rejects → create BusinessTransaction with REJECTED type)
PENDING → CANCELLED (not applicable in new 1:1 model — authoriser always exists)
```

---

### BusinessTransaction — NEW

Immutable record of an executed or rejected transaction on a `BusinessAccount`.

| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| `id` | BigAutoField PK | | |
| `business_account` | ForeignKey → BusinessAccount | PROTECT, related_name=`transactions` | |
| `transaction_type` | CharField(20) | choices below | |
| `amount` | DecimalField(12,2) | NOT NULL | |
| `balance_after` | DecimalField(12,2) | NOT NULL | Balance of BusinessAccount after this transaction |
| `counterparty` | ForeignKey → Account | SET_NULL, null/blank | For TRANSFER_OUT: recipient personal account |
| `description` | CharField(200) | blank | |
| `timestamp` | DateTimeField | auto_now_add | |

**transaction_type choices**: `DEPOSIT`, `WITHDRAWAL`, `TRANSFER_OUT`, `BILL_PAYMENT`, `REJECTED`

**Ordering**: `-timestamp`

---

### Account — UNCHANGED (personal accounts only)

`account_type` field and choices removed. `Account` is now exclusively personal.

| Field | Type | Notes |
|-------|------|-------|
| `id` | BigAutoField PK | |
| `user` | OneToOneField → CustomUser | |
| `balance` | DecimalField(12,2) | default 0.00 |
| `created_at` | DateTimeField | auto_now_add |

**Removed**: `account_type` CharField(10) and `PERSONAL`/`BUSINESS` choices

---

### BusinessProfile — DELETED

Replaced entirely by `BusinessAccount`. Removed in migration 0009.

---

## Migration 0009 — Changes

```
CREATE TABLE banking_businessaccount (...)
CREATE TABLE banking_accountmanagerprofile (...)
CREATE TABLE banking_businesstransaction (...)
ALTER TABLE banking_authoriser:
  DROP COLUMN assigned_by_id
  DROP COLUMN business_account_id  (old FK to Account)
  ADD COLUMN business_account_id FK → banking_businessaccount (OneToOne)
  RENAME user FK to OneToOneField
ALTER TABLE banking_pendingtransaction:
  RENAME COLUMN account_id → business_account_id
  ALTER FK target: Account → BusinessAccount
  DROP COLUMN biller_id
ALTER TABLE banking_account:
  DROP COLUMN account_type
DROP TABLE banking_businessprofile
```

Note: existing Authoriser and PendingTransaction rows (from old model) are dropped during
migration. Prototype tier — no production data to preserve.
