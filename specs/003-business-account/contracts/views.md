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

## GET /dashboard/ — MODIFIED (three-way branch: personal | manager | authoriser)

**View**: `banking.views.dashboard_view`

If the logged-in user has an `AccountManagerProfile`, the business account dashboard is rendered
instead of the personal dashboard.

**Branch order** (first match wins):
1. `hasattr(request.user, "manager_profile")` → manager dashboard
2. `hasattr(request.user, "authoriser_profile")` → authoriser dashboard
3. fallthrough → personal dashboard (unchanged)

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

**Business account authoriser dashboard** (Phase 2 — FR-005, FR-009a):

| Context variable | Value |
|-----------------|-------|
| `is_authoriser` | `True` |
| `business_account` | `Authoriser.business_account` |
| `balance` | `business_account.balance` |
| `recent_transactions` | Last 5 `BusinessTransaction` records for the business account |
| `deposit_form` | `DepositForm()` |
| `withdraw_form` | `WithdrawForm()` |
| `transfer_form` | `TransferForm()` |
| `bill_pay_form` | `BusinessBillPaymentForm()` |
| `authoriser_pending_count` | Count of `PendingTransaction` with status PENDING for the BA (via context processor) |

Pending-queue link rendered in template when `authoriser_pending_count > 0` (FR-009a).

---

## POST /banking/deposit/ — MODIFIED (account manager + authoriser branch)

**View**: `banking.views.deposit_view`

If the logged-in user has an `AccountManagerProfile` or `authoriser_profile`, calls
`deposit_to_business`. Both roles execute immediately.

| Outcome | HTTP Status | Description |
|---------|-------------|-------------|
| Valid amount (manager or authoriser) | 302 → dashboard | `deposit_to_business` executes; `BusinessTransaction` created; balance updated |
| Invalid amount (manager or authoriser) | 200 (form re-rendered) | Field-level error |
| Personal account path | unchanged | Same as before |

---

## POST /banking/withdraw/ — MODIFIED (account manager + authoriser branch)

**View**: `banking.views.withdraw_view`

Manager branch creates a `PendingTransaction` (balance unchanged). Authoriser branch calls
`withdraw_from_business` for immediate execution — FR-008a.

| Outcome | HTTP Status | Description |
|---------|-------------|-------------|
| Valid amount (manager) | 302 → dashboard | `create_pending_withdrawal` called; `PendingTransaction` status PENDING; balance unchanged |
| Valid amount (authoriser) | 302 → dashboard | `withdraw_from_business` called; `BusinessTransaction(WITHDRAWAL)` created; balance deducted immediately |
| Balance floor breach (manager) | 200 (form re-rendered) | `InsufficientFundsError`; no pending transaction created |
| Balance floor breach (authoriser) | 200 (form re-rendered) | `InsufficientFundsError`; no transaction created |
| Invalid amount | 200 (form re-rendered) | Field-level error |
| Personal account path | unchanged | Same as before |

---

## POST /banking/transfer/ — MODIFIED (account manager + authoriser branch)

**View**: `banking.views.transfer_view`

Manager branch creates a `PendingTransaction`. Authoriser branch calls `transfer_from_business`
for immediate execution — FR-008a.

| Outcome | HTTP Status | Description |
|---------|-------------|-------------|
| Valid recipient + amount (manager) | 302 → dashboard | `create_pending_transfer` called; `PendingTransaction` created; balance unchanged |
| Valid recipient + amount (authoriser) | 302 → dashboard | `transfer_from_business` called; `BusinessTransaction(TRANSFER_OUT)` created; balance deducted immediately |
| Recipient not found | 200 (form re-rendered) | Error: "No account found with that phone number." |
| Balance floor breach | 200 (form re-rendered) | `InsufficientFundsError`; no transaction created/queued |
| Personal account path | unchanged | Same as before |

---

## POST /banking/billing/pay/ — MODIFIED (account manager + authoriser branch)

**View**: `banking.views.pay_bill_view`

Both roles use `BusinessBillPaymentForm` (inline category + reference + amount). Manager branch
creates a `PendingTransaction`; authoriser branch calls `pay_bill_from_business` for immediate
execution — FR-008a.

| Outcome | HTTP Status | Description |
|---------|-------------|-------------|
| Valid form (manager) | 302 → dashboard | `create_pending_bill_payment` called; `PendingTransaction` created; balance unchanged |
| Valid form (authoriser) | 302 → dashboard | `pay_bill_from_business` called; `BusinessTransaction(BILL_PAYMENT)` created; balance deducted immediately |
| Balance floor breach | 200 (form re-rendered) | `InsufficientFundsError`; no transaction created/queued |
| Invalid amount | 200 (form re-rendered) | Field-level error |
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

## GET /banking/pending/ — NEW (Phase 2, manager read-only queue — FR-009)

**View**: `banking.views.manager_pending_view`

Read-only list of all `PENDING` transactions for the manager's `BusinessAccount`. No approve or
reject actions. Requires `AccountManagerProfile`; returns 403 if user lacks it.

| Outcome | HTTP Status | Description |
|---------|-------------|-------------|
| User has `AccountManagerProfile`, pending txns exist | 200 | Lists all pending transactions |
| User has `AccountManagerProfile`, no pending txns | 200 | Empty queue message |
| User does not have `AccountManagerProfile` | 403 | Forbidden |

**Context**:
```
pending_txns: PendingTransaction.objects.filter(
    business_account=request.user.manager_profile.business_account,
    status=PENDING
)
```

No POST handler — page is entirely read-only.

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
