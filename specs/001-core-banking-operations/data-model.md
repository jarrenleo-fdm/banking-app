# Data Model: Core Banking Operations

Generated: 2026-05-21 | Branch: `001-core-banking-operations`

---

## Entities

### CustomUser (`accounts` app)

Extends `AbstractBaseUser`. Replaces Django's built-in `User`.

| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| `id` | BigAutoField | PK | |
| `username` | CharField(150) | Case-insensitive unique (see below) | Original casing stored; lookup via `iexact` |
| `email` | EmailField | Unique; stored lowercase | Used for password reset and account identity |
| `name` | CharField(150) | Required | Full display name |
| `phone_number` | CharField(8) | Unique | 8 digits; first digit 8 or 9; normalized at save |
| `password` | CharField | — | Django Argon2 hash; managed by `AbstractBaseUser` |
| `is_active` | BooleanField | Default `True` | |
| `is_staff` | BooleanField | Default `False` | Django admin access |
| `date_joined` | DateTimeField | `auto_now_add=True` | |

**Case-insensitive username uniqueness** (Django 4.0+ functional index):
```python
class Meta:
    constraints = [
        UniqueConstraint(
            Lower('username'),
            name='unique_username_case_insensitive',
        )
    ]
```

**Phone number validation**: `RegexValidator(r'^[89]\d{7}$')` on the model
field; form `clean_phone_number()` strips whitespace and hyphens before
validation runs.

**`USERNAME_FIELD`**: `'username'` (used by Django admin and `createsuperuser`)
**`REQUIRED_FIELDS`**: `['email', 'name', 'phone_number']`

---

### Account (`banking` app)

Holds the monetary balance for one user. Created automatically when a
`CustomUser` is created (via `post_save` signal or explicit creation in the
registration service).

| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| `id` | BigAutoField | PK | |
| `user` | OneToOneField → CustomUser | `on_delete=CASCADE`; `related_name='account'` | One account per user |
| `balance` | DecimalField(12, 2) | Default `0.00` | Must always be ≥ 0; enforced in service layer |
| `created_at` | DateTimeField | `auto_now_add=True` | |

**Invariant**: `balance >= Decimal('0.00')` at all times. Never mutated directly
— always via `banking.services` functions that wrap in `@transaction.atomic`.

---

### Transaction (`banking` app)

Immutable record of one money movement. Created by service functions; never
updated or deleted.

| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| `id` | BigAutoField | PK | |
| `account` | ForeignKey → Account | `on_delete=PROTECT`; `related_name='transactions'` | The account whose balance changed |
| `transaction_type` | CharField(20) | Choices (see below) | |
| `amount` | DecimalField(12, 2) | Must be > 0 | Always a positive magnitude |
| `balance_after` | DecimalField(12, 2) | — | Snapshot of `account.balance` after this transaction |
| `counterparty` | ForeignKey → Account | `null=True`; `blank=True`; `on_delete=SET_NULL`; `related_name='counterparty_transactions'` | Other account in a transfer; `None` for deposits/withdrawals |
| `timestamp` | DateTimeField | `auto_now_add=True` | |
| `description` | CharField(200) | `blank=True` | Optional human-readable note |

**`transaction_type` choices**:

| Value | Label | Triggered by |
|-------|-------|--------------|
| `DEPOSIT` | Deposit | `services.deposit()` |
| `WITHDRAWAL` | Withdrawal | `services.withdraw()` |
| `TRANSFER_OUT` | Transfer Out | `services.transfer()` — sender's record |
| `TRANSFER_IN` | Transfer In | `services.transfer()` — recipient's record |

**Immutability**: `Transaction` objects have no update or delete paths in views
or services. The Django admin should set `readonly_fields` for all Transaction
fields (FR-025).

---

## Relationships

```
CustomUser ──(1:1)──> Account ──(1:N)──> Transaction (as primary account)
                                         Transaction (as counterparty, 0:1)
```

For a transfer between Account A (sender) and Account B (recipient), two
`Transaction` rows are created within a single `@transaction.atomic` block:

```
Transaction(account=A, type=TRANSFER_OUT, amount=X, counterparty=B)
Transaction(account=B, type=TRANSFER_IN,  amount=X, counterparty=A)
```

---

## State Transitions

### Account.balance

```
Created (balance=0.00)
    │
    ├── deposit(amount)     → balance += amount   [always valid if amount > 0]
    ├── withdraw(amount)    → balance -= amount   [valid only if balance >= amount]
    ├── transfer_out(amount)→ balance -= amount   [valid only if balance >= amount]
    └── transfer_in(amount) → balance += amount   [always valid if amount > 0]
```

### Transaction (immutable once created)

```
Created → [no further state transitions]
```

---

## Validation Rules

| Rule | Enforced at |
|------|-------------|
| `phone_number` matches `^[89]\d{7}$` | Model field validator + form `clean_phone_number()` |
| `username` case-insensitive unique | DB functional unique index + form validation |
| `email` unique (lowercase-normalized) | DB unique constraint + form validation |
| `amount > 0` for deposit/withdraw/transfer | Service layer (`services.py`) |
| `balance >= amount` before withdraw/transfer | Service layer (`services.py`) |
| Sender ≠ recipient in transfer | Service layer (`services.py`) |
| Recipient account must exist | Service layer — raises error if phone not found |
| Transaction records are never updated/deleted | No update/delete views or services exist |
| `balance` always reconciles with sum of transactions | Invariant maintained by service layer atomicity |

---

## Service Layer (`banking/services.py`)

All balance-modifying operations live here. Each function:
1. Accepts validated Python types (`Decimal` for amounts)
2. Wraps everything in `@transaction.atomic`
3. Re-reads the account balance inside the transaction (prevents stale-read race)
4. Raises a domain exception (`InsufficientFundsError`, `InvalidAmountError`,
   `RecipientNotFoundError`, `SelfTransferError`) on invalid input
5. Creates `Transaction` record(s) as the last step before commit

```python
# Prototype note: select_for_update() omitted for SQLite3 compatibility.
# Add Account.objects.select_for_update().get() when migrating to PostgreSQL.

@transaction.atomic
def deposit(account: Account, amount: Decimal) -> Transaction: ...

@transaction.atomic
def withdraw(account: Account, amount: Decimal) -> Transaction: ...

@transaction.atomic
def transfer(sender: Account, recipient_phone: str, amount: Decimal) -> tuple[Transaction, Transaction]: ...
```
