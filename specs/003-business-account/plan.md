# Implementation Plan: Business Account (Revised Model)

**Branch**: `003-business-account` | **Date**: 2026-05-26 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification — updated 2026-05-26 to incorporate Revised Role Model clarification.

## Summary

This plan covers two phases. Phase 1 (initial implementation, complete as of commit `a3970b3`) built
the public `/business/create` form, mock-SQL account creation, account manager dashboard, and the
authoriser approve/reject queue. Phase 2 (remaining, this plan update) implements the Revised Role
Model additions from the 2026-05-26 clarification session:

- **FR-008a** — Authoriser can submit all transaction types; outgoing transactions execute immediately
  (no pending queue for the authoriser's own submissions).
- **FR-005** for authoriser — Authoriser dashboard shows BusinessAccount balance and transaction
  history as the single source of truth.
- **FR-009** — Both manager and authoriser see the pending queue; manager view is read-only.
- **FR-009a** — Authoriser dashboard shows a visible pending-queue link whenever pending
  transactions exist.
- **FR-012(b)** — Minimum 7,000 balance enforced at authoriser direct submission (same floor as
  manager submission and authoriser approval).

## Technical Context

**Language/Version**: Python 3.11+, Django 5.2  
**Primary Dependencies**: Django 5.2, django-environ, argon2-cffi, pytest-django  
**Storage**: SQLite3 (prototype tier)  
**Testing**: pytest + pytest-django — Red-Green-Refactor per Constitution §II  
**Target Platform**: Local dev server (prototype)  
**Project Type**: Django web application (server-rendered)  
**Performance Goals**: Demo only — no throughput targets  
**Constraints**: SQLite3 `@transaction.atomic` suffices; no `select_for_update` required at prototype tier  
**Scale/Scope**: Single developer, demo audience

## Constitution Check

**Active Tier**: Prototype / Learning

| Principle | Status | Notes |
|---|---|---|
| I. Security (NON-NEGOTIABLE) | PASS | CSRF on all POSTs; `@login_required` on all protected views; `/business/create` is intentionally public |
| II. Test-First (NON-NEGOTIABLE) | REQUIRED | All new Phase 2 service functions and view branches must follow Red-Green-Refactor; tests written first, confirmed failing, then implemented |
| III. SonarQube | DEFERRED | Prototype tier — compensated by flake8/pylint/bandit locally (Complexity Tracking §1) |
| IV. Auditability | PASS | `BusinessTransaction` records every executed/rejected transaction immutably; all Phase 2 immediate-execution paths create `BusinessTransaction` records |
| V. Data Integrity | PASS | All balance mutations in `@transaction.atomic`; `select_for_update` not required at SQLite tier (Complexity Tracking §2) |

**Production Migration TODO**: Before involving real users or real money — migrate to PostgreSQL,
enable `select_for_update()`, integrate SonarQube CI, add full OWASP review.

## Project Structure

### Documentation (this feature)

```text
specs/003-business-account/
├── plan.md              # This file
├── research.md          # Phase 0 output (updated for Phase 2)
├── data-model.md        # Phase 1 output (no changes for Phase 2 — models are complete)
├── quickstart.md        # Phase 1 output (updated with Phase 2 flows)
├── contracts/
│   └── views.md         # Phase 1 output (updated with Phase 2 view contracts)
└── tasks.md             # Phase 2 output (/speckit-tasks)
```

### Source Code Layout

```text
banking/
├── models.py            ← complete (no changes for Phase 2)
├── services.py          ← MODIFY: add withdraw_from_business, transfer_from_business, pay_bill_from_business
├── views.py             ← MODIFY: add authoriser branch in dashboard_view; new manager_pending_view;
│                                    add authoriser branches in deposit_view, withdraw_view,
│                                    transfer_view, pay_bill_view
├── forms.py             ← no changes
├── urls.py              ← MODIFY: add /banking/pending/ URL for manager read-only queue
├── context_processors.py ← no changes (authoriser_pending_count already correct)
├── migrations/          ← no new migrations (schema is complete)
└── templates/banking/
    ├── dashboard.html         ← MODIFY: add authoriser branch rendering
    ├── manager_pending.html   ← ADD: read-only pending queue for account manager
    └── authoriser_queue.html  ← MODIFY: show BA balance/details in header
```

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|--------------------------------------|
| SonarQube not in CI (Principle III) | Prototype tier — no CI infra | Adds overhead disproportionate to demo scope; flake8/pylint/bandit compensate locally |
| `select_for_update` not used (Principle V) | SQLite3 backend | SQLite3 issues an exclusive write lock under `@transaction.atomic`; row-level locking not applicable |

## Phase 1: Completed (commit a3970b3)

All items below are implemented and tested.

### Deleted

| Item | Location |
|------|----------|
| `BusinessProfile` model | `banking/models.py` |
| `account_type` field on `Account` | `banking/models.py` |
| `manage_authorisers_view` + `add_authoriser_view` + `remove_authoriser_view` | `banking/views.py` |
| `dismiss_no_authoriser_warning_view` | `banking/views.py` |
| No-authoriser banner logic | `banking/views.py` |
| `pending_transactions_view` | `banking/views.py` |
| `AddAuthoriserForm` | `banking/forms.py` |
| `manage_authorisers/` URL family | `banking/urls.py` |
| `pending/` URL (old) | `banking/urls.py` |
| `manage_authorisers.html` template | `banking/templates/banking/` |

### Modified

| Item | Change |
|------|--------|
| `Authoriser` model | FK `Account` → `OneToOneField` `BusinessAccount`; `assigned_by` removed |
| `PendingTransaction` | `account` FK → `business_account` FK to `BusinessAccount`; `biller` FK removed |
| `dashboard_view` | Manager branch added (personal branch unchanged) |
| `deposit_view` | Manager branch calls `deposit_to_business` |
| `withdraw_view` | Manager branch creates `PendingTransaction` |
| `transfer_view` | Manager branch creates `PendingTransaction` |
| `pay_bill_view` | Manager branch uses `BusinessBillPaymentForm` → `PendingTransaction` |
| `authoriser_queue_view` | Uses `request.user.authoriser_profile.business_account` (1:1) |
| `approve_transaction_view` | Verifies `pending_tx.business_account.authoriser.user == request.user` |
| `reject_transaction_view` | Same verification |
| `context_processors.authoriser_pending_count` | Reads `authoriser_profile.business_account.pending_transactions` |

### Added

| Item | Location |
|------|----------|
| `BusinessAccount` model | `banking/models.py` |
| `AccountManagerProfile` model | `banking/models.py` |
| `BusinessTransaction` model | `banking/models.py` |
| `create_business_account_mock` | `banking/services.py` |
| `deposit_to_business` | `banking/services.py` |
| `create_pending_withdrawal` | `banking/services.py` |
| `create_pending_transfer` | `banking/services.py` |
| `create_pending_bill_payment` | `banking/services.py` |
| `approve_business_pending` | `banking/services.py` |
| `reject_business_pending` | `banking/services.py` |
| `BusinessCreateForm` | `banking/forms.py` |
| `BusinessBillPaymentForm` | `banking/forms.py` |
| `create_business_account_view` (GET + POST, public) | `banking/views.py` |
| `business_account_created_view` | `banking/views.py` |
| `create_business_account.html` | `banking/templates/banking/` |
| `business_account_created.html` | `banking/templates/banking/` |
| `/business/create/` URL | `banking/urls.py` |
| Migration 0009 | `banking/migrations/` |

## Phase 2: Remaining (Revised Role Model — clarification 2026-05-26)

### Service additions (banking/services.py)

Three new immediate-execution service functions for authoriser outgoing transactions. Each:
- Is wrapped in `@transaction.atomic`
- Enforces the 7,000 floor (`balance - amount < 7000.00` → raise `InsufficientFundsError`) — FR-012(b)
- Immediately deducts from `BusinessAccount.balance`
- Creates an immutable `BusinessTransaction` record

| Function | Signature |
|----------|-----------|
| `withdraw_from_business(ba, amount)` | Immediate withdrawal; creates `BusinessTransaction(WITHDRAWAL)` |
| `transfer_from_business(ba, amount, recipient_phone)` | Immediate transfer; creates `BusinessTransaction(TRANSFER_OUT)` |
| `pay_bill_from_business(ba, amount, category, reference)` | Immediate bill payment; creates `BusinessTransaction(BILL_PAYMENT)` |

### View additions / modifications (banking/views.py)

| Item | Change |
|------|--------|
| `dashboard_view` | Add authoriser branch: `elif hasattr(request.user, "authoriser_profile")` — renders BA balance, transaction history, transaction forms, and pending-queue link (FR-005, FR-009a) |
| `deposit_view` | Add authoriser branch: calls `deposit_to_business` (same as manager; deposit executes immediately) |
| `withdraw_view` | Add authoriser branch: calls `withdraw_from_business` (immediate execution — NOT pending queue) |
| `transfer_view` | Add authoriser branch: calls `transfer_from_business` (immediate execution) |
| `pay_bill_view` | Add authoriser branch: calls `pay_bill_from_business` (immediate execution) |
| `manager_pending_view` (NEW) | `GET /banking/pending/` — lists pending transactions for the manager's BA; read-only (no approve/reject); requires `AccountManagerProfile` |

### Template additions / modifications

| Template | Change |
|----------|--------|
| `dashboard.html` | Add authoriser context block; show pending-queue link when `authoriser_pending_count > 0` |
| `manager_pending.html` | NEW — read-only list of pending transactions for the business account |
| `authoriser_queue.html` | Add BA balance/company name in page header (consistent with FR-005) |

### URL additions (banking/urls.py)

| URL | View | Name |
|-----|------|------|
| `banking/pending/` | `manager_pending_view` | `manager_pending` |

## Key Design Decisions

### Business transaction recording
Separate `BusinessTransaction` model records all executed and rejected transactions for a `BusinessAccount`. This avoids making `Transaction.account` nullable and keeps personal transaction history clean.

### Authoriser immediate execution vs pending queue (FR-008a)
The authoriser's outgoing transactions call `withdraw_from_business` / `transfer_from_business` / `pay_bill_from_business` (new) — these execute and commit balance changes immediately. They do NOT create `PendingTransaction` records. This avoids a deadlock where the only authoriser (1:1 model) cannot approve their own submissions.

### Three-way dashboard branching (FR-005)
`dashboard_view` branches on `AccountManagerProfile` presence (manager), then `Authoriser` presence (authoriser), then falls through to personal. Both business-role branches read balance and transaction history exclusively from `BusinessAccount` — no personal `Account` data is shown for either role.

### Manager read-only pending queue (FR-009)
A dedicated `manager_pending_view` at `GET /banking/pending/` returns the pending transaction list for the manager's `BusinessAccount` without approve/reject controls. Only accessible to users with `AccountManagerProfile`. Prevents manager from discovering the approve/reject endpoints by URL guessing (HTTP 403 if they POST to the authoriser queue).

### Phone number generation for demo accounts
Manager users get the next odd slot in the `8xxxxxxx` range (80000001, 80000003, …); authoriser users get the next even slot (80000002, 80000004, …). Service queries existing phone numbers before each assignment.

### Username uniqueness
Generated usernames follow `manager.<slug>` / `authoriser.<slug>` where `<slug>` is the business name lowercased and stripped of non-alphanumeric characters (max 20 chars). A numeric suffix resolves collisions.
