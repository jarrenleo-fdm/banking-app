# Data Model: UX Enhancements

## Summary

No schema changes. All required fields (`Transaction.description`, `Transaction.counterparty`) are present in the initial migration. Changes are confined to application logic, forms, services, and templates.

---

## Entities

### Transaction (existing — no schema change)

| Field | Type | Constraints | Notes |
|---|---|---|---|
| `id` | BigAutoField | PK, auto-increment | Used as the visible Transaction ID |
| `account` | FK → Account | NOT NULL, PROTECT | Owner of this transaction entry |
| `transaction_type` | CharField(20) | choices: DEPOSIT, WITHDRAWAL, TRANSFER_OUT, TRANSFER_IN | |
| `amount` | DecimalField(12,2) | NOT NULL | Always positive |
| `balance_after` | DecimalField(12,2) | NOT NULL | Snapshot of balance after this tx |
| `counterparty` | FK → Account | NULL, blank, SET_NULL | Sender (TRANSFER_IN) or recipient (TRANSFER_OUT) |
| `timestamp` | DateTimeField | auto_now_add | Immutable |
| `description` | CharField(200) | blank=True | Optional; written for both TRANSFER_OUT and TRANSFER_IN |

**Behaviour change**: `transfer()` service must accept `description: str = ""` and write it to both the TRANSFER_OUT and TRANSFER_IN records it creates.

---

### Account (existing — no schema change)

| Field | Type | Constraints | Notes |
|---|---|---|---|
| `id` | BigAutoField | PK | |
| `user` | OneToOneField → CustomUser | CASCADE | |
| `balance` | DecimalField(12,2) | default 0.00 | Set to `initial_balance` after signal creates it with 0 |
| `created_at` | DateTimeField | auto_now_add | |

**Behaviour change**: After user registration, if the submitted `initial_balance` is greater than zero, `signup_view` updates `account.balance` and saves with `update_fields=["balance"]`.

---

### CustomUser (existing — no change)

No changes to the user model.

---

### PasswordComplexityValidator (new — application logic only, no schema)

A new custom validator class to be added to the `accounts` app and registered in `AUTH_PASSWORD_VALIDATORS`. Enforces:

| Criterion | Rule |
|---|---|
| Minimum length | ≥ 8 characters (already enforced by MinimumLengthValidator) |
| Uppercase letter | At least one character in A–Z |
| Lowercase letter | At least one character in a–z |
| Digit | At least one character in 0–9 |
| Special character | At least one character not in A–Z, a–z, 0–9 |

**Note**: `MinimumLengthValidator` remains in `AUTH_PASSWORD_VALIDATORS` for the standard length error message; the new validator enforces the character class rules.

---

## Validation Rules

| Rule | Scope | Enforcement |
|---|---|---|
| `initial_balance` ≥ 0 | Registration form | `RegistrationForm.clean_initial_balance()` — reject negative values |
| `initial_balance` numeric | Registration form | Django `DecimalField` type validation |
| `description` max 200 chars | Transfer form | `TransferForm.description` field `max_length=200` |
| Password complexity | Registration + reset | `PasswordComplexityValidator` in `AUTH_PASSWORD_VALIDATORS` |

---

## State Transitions

No new state transitions. The existing deposit/withdraw/transfer flow is unchanged; the description parameter is additive.
