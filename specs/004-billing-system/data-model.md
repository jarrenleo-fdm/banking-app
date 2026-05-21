# Data Model: Billing System

## New Entity: Biller

Represents a payee saved by a user for repeated bill payments. The biller category is selected from a fixed list — free-text names are not supported.

| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| `id` | Auto PK | — | |
| `account` | FK → Account | CASCADE delete, `related_name="billers"` | One user = one account |
| `name` | CharField(50, choices=BILLER_CATEGORIES) | NOT NULL | One of five predefined categories (see below) |
| `reference` | CharField(100) | NOT NULL, **mandatory** | Customer/account number with the biller — required, free-text |
| `created_at` | DateTimeField | auto_now_add | |

**Predefined categories** (`BILLER_CATEGORIES` constant on `Biller`):

| Stored value | Display label |
|---|---|
| `ELECTRICITY` | Electricity |
| `WATER_UTILITIES` | Water & Utilities |
| `INTERNET_BROADBAND` | Internet & Broadband |
| `TELECOMMUNICATIONS` | Telecommunications |
| `TOWN_COUNCIL` | Town Council / Maintenance |

**Uniqueness constraint** (`unique_together = [("account", "name", "reference")]`):
- The combination (account, category, reference) must be unique — two billers for the same user and same category cannot share the same reference string.
- The same reference string may appear under different categories (e.g., "12345" for both Electricity and Internet).

**Validation rules**:
- `name` must be one of the five defined category values; any other value is rejected at the model and form level.
- `reference` is mandatory — the add-biller form cannot be submitted without it.
- A user may save the same category more than once provided each entry has a distinct reference (e.g., two Electricity billers for two premises with different account numbers).

**`__str__`**: Returns `"{display_name} ({reference})"` — e.g., `"Electricity (ACC-001)"`. This is the label shown in the BillPaymentForm dropdown and in the payment success message.

**Migration note**: Migration `0005_biller_reference_mandatory_unique` (new) performs two operations:
1. `AlterField` — removes `blank=True` from `reference` (CharField remains NOT NULL with empty-string default for existing rows; no data loss in Prototype/SQLite3).
2. `AddConstraint` — adds `unique_together = [("account", "name", "reference")]`.

**Relationships**:
- `Biller` → `Account` (many-to-one). One account can have many billers.

---

## Amended Entity: Transaction

The existing `Transaction` model gains one new type value.

| Change | Detail |
|--------|--------|
| Add constant | `BILL_PAYMENT = "BILL_PAYMENT"` |
| Add to `TRANSACTION_TYPES` | `(BILL_PAYMENT, "Bill Payment")` |

No new columns are added. The `description` field (already `CharField(200)`, blank=True) stores `"{category} ({reference})"` at payment time (e.g., `"Electricity (ACC-001)"`), making the record self-contained even if the `Biller` row is later deleted.

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

**Migration 0004** (already applied): Amends `Biller.name` to add choices and reduce `max_length` from 100 → 50.

**Migration 0005** (new — this plan): Removes `blank=True` from `Biller.reference`; adds `unique_together = [("account", "name", "reference")]`.
