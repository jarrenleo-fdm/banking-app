# Data Model: Business Account Registration

## Summary

Two schema changes: `Account` gains an `account_type` field, and a new `BusinessProfile` table is added. All existing data is unaffected (default value backfills `account_type = PERSONAL` for all existing rows). No changes to `Transaction`, `CustomUser`, or any other model.

---

## Entities

### Account (existing — modified)

| Field | Type | Constraints | Notes |
|---|---|---|---|
| `id` | BigAutoField | PK | Unchanged |
| `user` | OneToOneField → CustomUser | CASCADE | Unchanged |
| `balance` | DecimalField(12,2) | default 0.00 | Unchanged |
| `created_at` | DateTimeField | auto_now_add | Unchanged |
| `account_type` | CharField(10) | choices: PERSONAL / BUSINESS, default PERSONAL, NOT NULL | **NEW** — set to BUSINESS in signup_view for business registrations; PERSONAL by default for all existing and new personal accounts |

**Behaviour change**: `signup_view` updates `account.account_type` after the `post_save` signal creates the account, using `save(update_fields=["account_type"])`.

---

### BusinessProfile (new)

| Field | Type | Constraints | Notes |
|---|---|---|---|
| `id` | BigAutoField | PK, auto-increment | |
| `account` | OneToOneField → Account | CASCADE, related_name="business_profile" | One business profile per account |
| `company_name` | CharField(200) | NOT NULL | Free-text; stripped of leading/trailing whitespace on save |
| `business_registration_number` | CharField(20) | NOT NULL, unique | Alphanumeric 6–20 chars; validated by RegexValidator(`^[A-Za-z0-9]{6,20}$`) |

**Behaviour change**: `signup_view` calls `BusinessProfile.objects.create(account=account, ...)` after setting `account.account_type = BUSINESS`.

---

### CustomUser (existing — unchanged)

No changes to the user model.

---

### Transaction (existing — unchanged)

No changes to the transaction model or any money-moving code paths.

---

## Validation Rules

| Rule | Scope | Enforcement |
|---|---|---|
| `account_type` is PERSONAL or BUSINESS | Registration form | ChoiceField in `RegistrationForm` |
| `company_name` required when `account_type == BUSINESS` | Registration form | `RegistrationForm.clean()` |
| `business_registration_number` required when `account_type == BUSINESS` | Registration form | `RegistrationForm.clean()` |
| `business_registration_number` format: alphanumeric, 6–20 chars | Registration form + model | `RegexValidator` on form field; DB stores whatever passes form validation |
| `business_registration_number` unique | Registration form | `RegistrationForm.clean_business_registration_number()` queries existing `BusinessProfile` records |
| `company_name` not blank/whitespace-only | Registration form | `RegistrationForm.clean()` strips and checks |

---

## Migration

**File**: `banking/migrations/0002_account_type_business_profile.py`

Operations:
1. `AddField` — `Account.account_type` (CharField, default PERSONAL, preserve_default=False after migration)
2. `CreateModel` — `BusinessProfile` with OneToOne to Account

Both operations are reversible (RunSQL not used; standard Django ORM operations only).

---

## State Transitions

No new state transitions for money or security events. `account_type` is set once at registration and is not user-editable after creation (out of scope per spec).
