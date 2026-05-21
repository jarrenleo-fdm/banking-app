# View Contracts: Business Account Registration

This document describes the HTTP view contracts that change for this feature. All other views are unaffected.

---

## POST /accounts/signup/ — modified

**View**: `accounts.views.signup_view`

### Request

| Field | Type | Required | Validation |
|---|---|---|---|
| `name` | string | Yes | Non-empty |
| `username` | string | Yes | Unique (case-insensitive), max 150 chars |
| `email` | string | Yes | Valid email, unique |
| `phone_number` | string | Yes | Format: `^[89]\d{7}$` (Singapore), unique |
| `password1` | string | Yes | Passes all `AUTH_PASSWORD_VALIDATORS` |
| `password2` | string | Yes | Matches `password1` |
| `initial_balance` | decimal | No | ≥ 0.00, defaults to 0.00 |
| `account_type` | string | Yes | One of: `PERSONAL`, `BUSINESS` |
| `company_name` | string | Conditional | Required when `account_type == BUSINESS`; non-blank after strip |
| `business_registration_number` | string | Conditional | Required when `account_type == BUSINESS`; alphanumeric 6–20 chars; unique |

### Responses

| Outcome | HTTP Status | Description |
|---|---|---|
| Successful personal registration | 302 → `/banking/dashboard/` | User created, personal account active, user logged in |
| Successful business registration | 302 → `/banking/dashboard/` | User created, business profile created, account_type set to BUSINESS, user logged in |
| Validation error (any field) | 200 (form re-rendered) | Form displayed with field-level error messages; no user or profile created |
| Duplicate `business_registration_number` | 200 (form re-rendered) | Error on `business_registration_number` field: "This registration number is already in use." |
| Missing business fields when `account_type == BUSINESS` | 200 (form re-rendered) | Errors on `company_name` and/or `business_registration_number` fields |

### Side Effects (on success)

1. `CustomUser` created with provided credentials.
2. `Account` created by `post_save` signal with `account_type = PERSONAL` (default).
3. If `account_type == BUSINESS`:
   - `account.account_type` updated to `BUSINESS` via `save(update_fields=["account_type"])`.
   - `BusinessProfile` created with `company_name` and `business_registration_number`.
4. If `initial_balance > 0`: `account.balance` updated via `save(update_fields=["balance"])`.
5. User is logged in (`login(request, user)`).

---

## GET /accounts/signup/ — modified (template only)

**View**: `accounts.views.signup_view` (no logic change for GET)

### Response

Renders `accounts/signup.html` with the extended `RegistrationForm`. The template shows:
- Account type selector (Personal / Business) — Personal selected by default.
- Standard registration fields (name, username, email, phone_number, password1, password2, initial_balance).
- Business fields section (company_name, business_registration_number) — **hidden by default**, revealed via inline JavaScript when "Business" is selected.

---

## GET /banking/dashboard/ — modified (template only)

**View**: `banking.views.dashboard_view` (no logic change)

### Response

Template (`banking/dashboard.html`) now displays the account type label alongside the account balance. Label values:

| `account.account_type` | Displayed label |
|---|---|
| `PERSONAL` | Personal |
| `BUSINESS` | Business |

No additional context data is required from the view; `request.user.account.account_type` is accessible in the template via the existing `account` context variable (or `request.user.account` directly).
