# Data Model: Billing System

## New Entity: Biller

Represents a payee saved by a user for repeated bill payments. The biller category is selected from a fixed list — free-text names are not supported.

| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| `id` | Auto PK | — | |
| `account` | FK → Account | CASCADE delete, `related_name="billers"` | One user = one account |
| `name` | CharField(50, choices=BILLER_CATEGORIES) | NOT NULL | One of five predefined categories (see below) |
| `reference` | CharField(100) | blank=True | Optional customer/account number with the biller |
| `created_at` | DateTimeField | auto_now_add | |

**Predefined categories** (`BILLER_CATEGORIES` constant on `Biller`):

| Stored value | Display label |
|---|---|
| `ELECTRICITY` | Electricity |
| `WATER_UTILITIES` | Water & Utilities |
| `INTERNET_BROADBAND` | Internet & Broadband |
| `TELECOMMUNICATIONS` | Telecommunications |
| `TOWN_COUNCIL` | Town Council / Maintenance |

**Validation rules**:
- `name` must be one of the five defined category values; any other value is rejected at the model and form level.
- A user may save the same category more than once with different references (e.g., two Electricity billers for two premises). No uniqueness constraint on `(account, name)`.

**Migration note**: This is a choices-only change on an existing `CharField`. The underlying column width may shrink from 100 → 50 characters, which requires a schema migration but involves no data loss (existing rows used free-text values that are shorter than 50 chars in testing; production would require a data migration).

**Relationships**:
- `Biller` → `Account` (many-to-one). One account can have many billers.

---

## Amended Entity: Transaction

The existing `Transaction` model gains one new type value.

| Change | Detail |
|--------|--------|
| Add constant | `BILL_PAYMENT = "BILL_PAYMENT"` |
| Add to `TRANSACTION_TYPES` | `(BILL_PAYMENT, "Bill Payment")` |

No new columns are added. The `description` field (already `CharField(200)`, blank=True) stores the biller name at the time of payment, making the record self-contained even if the `Biller` row is later deleted.

**State transitions** (bill payment flow):
```
User selects Biller + enters amount
  → validate amount > 0
  → validate account.balance >= amount
  → BEGIN ATOMIC
      account.balance -= amount
      Transaction(type=BILL_PAYMENT, description=biller.name) created
  → END ATOMIC
```

---

## Migrations

**Migration 0003** (already applied): Creates the `Biller` table; adds `BILL_PAYMENT` to `Transaction.TRANSACTION_TYPES`.

**Migration 0004** (new — this plan): Amends `Biller.name` to add choices and reduce `max_length` from 100 → 50. This is a schema change (column width reduction) and must be applied before any production deployment. In the Prototype/Learning tier with SQLite3 and a clean test database, this is a safe `AlterField` operation.
