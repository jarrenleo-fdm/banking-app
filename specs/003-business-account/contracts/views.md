# View Contracts: Business Account (Revised Model)

All existing personal account views (`deposit_view`, `withdraw_view`, `transfer_view`,
`pay_bill_view`, `billing_view`, etc.) are unchanged for users without an `AccountManagerProfile`.
Only the branching logic and new views are documented here.

---

## GET /business/create/ — NEW (public, no login required)

**View**: `banking.views.create_business_account_view`

Renders the business account creation form.

| Outcome | HTTP Status | Description |
|---------|-------------|-------------|
| Normal render | 200 | Form with fields: company_name, uen, street, city, postal_code |

---

## POST /business/create/ — NEW (public, no login required)

**View**: `banking.views.create_business_account_view`

Validates form and calls `create_business_account_mock`. On success, redirects to confirmation.

| Outcome | HTTP Status | Description |
|---------|-------------|-------------|
| Valid submission, UEN unique | 302 → `/business/created/?id=<biz_id>` | `BusinessAccount` created; manager + authoriser users created; credentials in session |
| Blank required field | 200 (form re-rendered) | Field-level validation errors; no account created |
| Duplicate UEN | 200 (form re-rendered) | Error on `uen` field: "A business account with this UEN already exists." |

**Session handling**: Credentials (manager username/password, authoriser username/password,
phone numbers) are stored in `request.session` under `business_created_credentials` and
displayed once on the confirmation screen. Session key is cleared after display.

---

## GET /business/created/ — NEW (public)

**View**: `banking.views.business_account_created_view`

Reads credentials from session and renders the one-time confirmation screen.

| Outcome | HTTP Status | Description |
|---------|-------------|-------------|
| Credentials in session | 200 | Shows manager + authoriser usernames, passwords, phone numbers |
| No credentials in session (direct URL visit or refresh) | 302 → `/business/create/` | Credentials already consumed; redirect back to form |

---

## GET /dashboard/ — MODIFIED (account manager branch)

**View**: `banking.views.dashboard_view`

If the logged-in user has an `AccountManagerProfile`, the business account dashboard is rendered
instead of the personal dashboard.

**Personal dashboard** (no `AccountManagerProfile`): unchanged.

**Business account manager dashboard**:

| Context variable | Value |
|-----------------|-------|
| `is_manager` | `True` |
| `business_account` | `AccountManagerProfile.business_account` |
| `balance` | `business_account.balance` |
| `recent_transactions` | Last 5 `BusinessTransaction` records for the business account |
| `deposit_form` | `DepositForm()` |
| `withdraw_form` | `WithdrawForm()` |
| `transfer_form` | `TransferForm()` |
| `bill_pay_form` | `BusinessBillPaymentForm()` (inline: category + reference + amount) |

No "no-authoriser" banner — authoriser always exists in the new model.

---

## POST /banking/deposit/ — MODIFIED (account manager branch)

**View**: `banking.views.deposit_view`

If the logged-in user has an `AccountManagerProfile`, calls `deposit_to_business` instead of
`deposit`.

| Outcome | HTTP Status | Description |
|---------|-------------|-------------|
| Valid amount (manager) | 302 → dashboard | `deposit_to_business` executes; `BusinessTransaction` created; balance updated |
| Invalid amount (manager) | 200 (form re-rendered) | Field-level error |
| Personal account path | unchanged | Same as before |

---

## POST /banking/withdraw/ — MODIFIED (account manager branch)

**View**: `banking.views.withdraw_view`

If the logged-in user has an `AccountManagerProfile`, creates a `PendingTransaction` for the
`BusinessAccount`. No authoriser-existence check (authoriser always exists in new model).

| Outcome | HTTP Status | Description |
|---------|-------------|-------------|
| Valid amount (manager) | 302 → dashboard | `PendingTransaction` created with status PENDING; balance unchanged |
| Insufficient funds (manager) | 200 (form re-rendered) | Error: "Insufficient funds." |
| Invalid amount (manager) | 200 (form re-rendered) | Field-level error |
| Personal account path | unchanged | Same as before |

---

## POST /banking/transfer/ — MODIFIED (account manager branch)

**View**: `banking.views.transfer_view`

If the logged-in user has an `AccountManagerProfile`, creates a `PendingTransaction` (type
`TRANSFER_OUT`) for the `BusinessAccount`. Balance unchanged until authoriser approves.

| Outcome | HTTP Status | Description |
|---------|-------------|-------------|
| Valid recipient + amount (manager) | 302 → dashboard | `PendingTransaction` created; `counterparty` set to recipient `Account` |
| Recipient not found (manager) | 200 (form re-rendered) | Error: "No account found with that phone number." |
| Insufficient funds (manager) | 200 (form re-rendered) | Error: "Insufficient funds." |
| Personal account path | unchanged | Same as before |

---

## POST /banking/billing/pay/ — MODIFIED (account manager branch)

**View**: `banking.views.pay_bill_view`

If the logged-in user has an `AccountManagerProfile`, the `BusinessBillPaymentForm` (inline
biller category + reference + amount) is used instead of the saved-biller form. Creates a
`PendingTransaction` (type `BILL_PAYMENT`) for the `BusinessAccount`.

| Outcome | HTTP Status | Description |
|---------|-------------|-------------|
| Valid form (manager) | 302 → dashboard | `PendingTransaction` created; description = "Category (reference)" |
| Invalid amount (manager) | 200 (form re-rendered) | Field-level error |
| Personal account path | unchanged | Same as before |

---

## GET /banking/authorise/ — MODIFIED

**View**: `banking.views.authoriser_queue_view`

Uses `request.user.authoriser_profile.business_account` (1:1) instead of queryset.

| Outcome | HTTP Status | Description |
|---------|-------------|-------------|
| User is authoriser, pending txns exist | 200 | Lists pending transactions for their business account |
| User is authoriser, no pending txns | 200 | Empty queue message |
| User is not an authoriser | 403 | "You are not assigned as an authoriser." |

**Context**:
```
pending_txns: PendingTransaction.objects.filter(
    business_account=request.user.authoriser_profile.business_account,
    status=PENDING
)
```

---

## POST /banking/authorise/<id>/approve/ — MODIFIED

**View**: `banking.views.approve_transaction_view`

Authorization check: `pending_tx.business_account.authoriser.user == request.user`.

| Outcome | HTTP Status | Description |
|---------|-------------|-------------|
| Valid authoriser, transaction PENDING | 302 → authoriser queue | `approve_business_pending` called; `BusinessTransaction` created; balance updated |
| Valid authoriser, insufficient funds | 302 → authoriser queue | Error flash; transaction stays PENDING |
| Not the authoriser for this business account | 403 | Forbidden |

---

## POST /banking/authorise/<id>/reject/ — MODIFIED

**View**: `banking.views.reject_transaction_view`

Authorization check: `pending_tx.business_account.authoriser.user == request.user`.

| Outcome | HTTP Status | Description |
|---------|-------------|-------------|
| Valid authoriser, transaction PENDING | 302 → authoriser queue | `reject_business_pending` called; `BusinessTransaction` created with type REJECTED |
| Not the authoriser for this business account | 403 | Forbidden |

---

## DELETED views

The following views are removed entirely (no replacement):

| View | Reason |
|------|--------|
| `manage_authorisers_view` | Authoriser is auto-created; no manual management needed |
| `add_authoriser_view` | Same |
| `remove_authoriser_view` | Same |
| `dismiss_no_authoriser_warning_view` | No-authoriser warning removed; authoriser always exists |
| `pending_transactions_view` | Account owner can no longer view the pending queue directly (only the authoriser can) |
