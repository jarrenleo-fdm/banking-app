# View Contracts: Billing System

All endpoints require authentication (`@login_required`). All POST endpoints require CSRF token and are decorated with `@require_POST`.

---

## GET /banking/billing/

**Purpose**: Billing home — list saved billers and display the "Pay a bill" form.

**Auth**: Login required  
**Template**: `banking/billing.html`

**Context**:
```
billers        — QuerySet of Biller objects for request.user.account, ordered by name
pay_form       — BillPaymentForm (pre-populated with first biller if any exist)
add_biller_form — BillerForm (empty)
account        — request.user.account
```

**Success**: Renders billing page.

---

## POST /banking/billing/biller/add/

**Purpose**: Add a new biller for the logged-in user.

**Auth**: Login required  
**Form**: `BillerForm` (fields: `name`, `reference`)

**Success**: Redirect to `banking:billing`  
**Failure**: Re-render billing page with `add_biller_form` errors, HTTP 200

**Validation**:
- `name` — required, must be one of the five predefined category values (`ELECTRICITY`, `WATER_UTILITIES`, `INTERNET_BROADBAND`, `TELECOMMUNICATIONS`, `TOWN_COUNCIL`); rendered as a `<select>` dropdown, not a text input
- `reference` — optional, max 100 chars, free-text

---

## POST /banking/billing/biller/\<biller_id\>/remove/

**Purpose**: Remove a saved biller owned by the logged-in user.

**Auth**: Login required  
**URL param**: `biller_id` (integer PK)

**Success**: Redirect to `banking:billing`  
**Not found / wrong owner**: 404 (never leak existence to non-owners)

---

## POST /banking/billing/pay/

**Purpose**: Execute a bill payment from the user's account.

**Auth**: Login required  
**Form**: `BillPaymentForm` (fields: `biller` (PK, scoped to user), `amount`)

**Success**: Redirect to `banking:billing` with success message  
**Failure**: Re-render billing page with `pay_form` errors, HTTP 200

**Service errors mapped to form errors**:
| Exception | Field | Message |
|-----------|-------|---------|
| `InvalidAmountError` | `amount` | "Amount must be greater than zero." |
| `InsufficientFundsError` | `amount` | "Insufficient funds." |

---

## GET /banking/billing/history/

**Purpose**: Bill payment history for the logged-in user.

**Auth**: Login required  
**Template**: `banking/billing_history.html`

**Context**:
```
account       — request.user.account
payments      — Transaction QuerySet filtered to BILL_PAYMENT type for account, ordered -timestamp
```
