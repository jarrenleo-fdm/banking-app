# Data Model: UX Enhancements

## Summary

No schema changes. All required fields (`Transaction.description`, `Transaction.counterparty`, `CustomUser.name`, `CustomUser.username`, `CustomUser.email`, `CustomUser.phone_number`, and password hash storage) already exist. Changes are confined to application logic, forms, views, services, templates, and non-PII logging.

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
| `balance` | DecimalField(12,2) | default 0.00 | Increased through deposit when signup includes a positive initial balance |
| `created_at` | DateTimeField | auto_now_add | |

**Behaviour change**: After user registration, if the submitted `initial_balance` is greater than zero, the application applies it through the existing `deposit()` service so account balance and transaction history reconcile.

---

### CustomUser / User Profile (existing — no schema change)

| Field | Type | Constraints | Notes |
|---|---|---|---|
| `id` | BigAutoField | PK | Used internally to identify the signed-in user |
| `username` | CharField(150) | unique, case-insensitive | Editable login identifier |
| `name` | CharField(150) | required | Editable display/account-holder name |
| `email` | EmailField | unique, normalized lowercase | Editable contact email |
| `phone_number` | CharField(8) | unique, `^[89]\d{7}$` | Editable transfer/contact identifier; spaces and hyphens normalized before save |
| `is_active` | BooleanField | default True | Not editable in this flow |

**Behaviour change**: Add an authenticated user details update flow that edits `name`, `username`, `email`, and `phone_number` for the current user only. Username changes affect future logins but do not rewrite historical transaction records.

---

### Account Credentials (existing — no schema change)

| Field | Type | Constraints | Notes |
|---|---|---|---|
| `username` | CharField(150) | unique, accepted username format | Editable login identifier on the profile page |
| `password` | Hashed password field | managed by Django password APIs | Never displayed; changed only after current-password verification |

**Behaviour change**: Add a signed-in password change path that requires the current password, validates a matching new password against the same password criteria used for signup and password reset, saves the new password hash, and preserves the user's authenticated session.

**Audit/log rule**: Successful profile updates emit a security-relevant log/audit event with acting user id and changed field names only; raw email addresses and phone numbers must not be logged.

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
| Password complexity | Registration + reset + signed-in password change | `PasswordComplexityValidator` in `AUTH_PASSWORD_VALIDATORS` |
| `name` present | User details form | Reject blank name |
| `username` valid and unique | User details form | Use accepted username format; exclude current user from uniqueness conflict checks |
| `email` valid and unique | User details form | Normalize lowercase; exclude current user from uniqueness conflict checks |
| `phone_number` valid and unique | User details form | Normalize spaces/hyphens; require Singapore-style 8 digit number beginning with 8 or 9; exclude current user from uniqueness conflict checks |
| Current password correct | Password change form | Reject password changes unless the current password matches the signed-in user |
| New password confirmation matches | Password change form | Reject password changes when confirmation differs |

---

## State Transitions

### Transfer description

No state transition change. The existing deposit/withdraw/transfer flow is unchanged; the description parameter is additive.

### Initial balance

`Registered user with zero balance` -> `Registered user with deposited opening balance`

- Trigger: Signup includes `initial_balance > 0`.
- Result: Account balance increases by the submitted amount and a deposit transaction records the opening balance event.

### User profile update

`Current saved profile details` -> `Updated saved profile details`

- Trigger: Authenticated user submits valid changes to name, username, email address, or phone number.
- Guards: User must be authenticated; submitted identity/contact details must pass format and uniqueness validation.
- Result: Changed details are saved for the current user, future logins use the updated username, and the update is visible immediately.
- Failure path: If any submitted field is invalid or conflicts with another account, no submitted profile details are saved.

### Password change

`Current password credential` -> `Updated password credential`

- Trigger: Authenticated user submits the correct current password plus a valid matching new password and confirmation.
- Guards: User must be authenticated; current password must match; new password must satisfy all password criteria; confirmation must match.
- Result: The password hash is updated, the user's session remains valid, future logins require the new password, and the old password no longer authenticates.
- Failure path: If any password field is invalid, the password remains unchanged and the user receives field-specific errors.
