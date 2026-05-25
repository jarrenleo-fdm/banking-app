# Implementation Plan: Business Account (Revised Model)

**Branch**: `main` | **Date**: 2026-05-25 | **Spec**: [spec.md](spec.md)
**Input**: Revised feature specification — business account as standalone entity with mock SQL creation

## Summary

Add a public `/business/create` form (business name, UEN, address only) that runs mock SQL to
produce a `BusinessAccount` entity plus two auto-credentialed user accounts: an account manager
(can submit all transaction types against the business account) and an authoriser (approves or
rejects outgoing transactions before they execute). The business account is not a login account.
Existing personal account infrastructure is unchanged.

## Technical Context

**Language/Version**: Python 3.14.5
**Primary Dependencies**: Django 5.x, django-environ, argon2-cffi, pytest-django
**Storage**: SQLite3 (prototype tier)
**Testing**: pytest + pytest-django — Red-Green-Refactor per Constitution §II
**Target Platform**: Local dev server (prototype)
**Project Type**: Django web application (server-rendered)
**Performance Goals**: Demo only — no throughput targets
**Constraints**: SQLite3 `@transaction.atomic` suffices (no `select_for_update` required at prototype tier)
**Scale/Scope**: Single developer, demo audience

## Constitution Check

**Active Tier**: Prototype / Learning

| Principle | Status | Notes |
|---|---|---|
| I. Security (NON-NEGOTIABLE) | PASS | CSRF on all POSTs; `@login_required` on all protected views; `/business/create` is intentionally public |
| II. Test-First (NON-NEGOTIABLE) | REQUIRED | All service functions and views must follow Red-Green-Refactor |
| III. SonarQube | DEFERRED | Prototype tier — compensated by flake8/pylint/bandit locally (Complexity Tracking §1) |
| IV. Auditability | PASS | `BusinessTransaction` records every executed/rejected transaction immutably |
| V. Data Integrity | PASS | All balance mutations in `@transaction.atomic`; `select_for_update` not required at SQLite tier (Complexity Tracking §2) |

**Production Migration TODO**: Before involving real users or real money — migrate to PostgreSQL,
enable `select_for_update()`, integrate SonarQube CI, add full OWASP review.

## Project Structure

### Documentation (this feature)

```text
specs/003-business-account/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/
│   └── views.md         # Phase 1 output
└── tasks.md             # Phase 2 output (/speckit-tasks — not yet generated)
```

### Source Code Layout

```text
banking/
├── models.py
├── services.py
├── views.py
├── forms.py
├── urls.py
├── admin.py
├── context_processors.py
├── migrations/
│   └── 0009_business_account_revised_model.py
└── templates/banking/
    ├── create_business_account.html   ← NEW
    ├── business_account_created.html  ← NEW (credential confirmation screen)
    ├── dashboard.html                 ← MODIFIED
    ├── pending_transactions.html      ← MODIFIED
    ├── authoriser_queue.html          ← MODIFIED
    └── manage_authorisers.html        ← DELETE
```

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|--------------------------------------|
| SonarQube not in CI (Principle III) | Prototype tier — no CI infra | Adds overhead disproportionate to demo scope; flake8/pylint/bandit compensate locally |
| `select_for_update` not used (Principle V) | SQLite3 backend | SQLite3 issues an exclusive write lock under `@transaction.atomic`; row-level locking not applicable |

## Cleanup Enumeration

### DELETE — code from the wrong model

| Item | Location |
|------|----------|
| `BusinessProfile` model | `banking/models.py` |
| `account_type` field + choices on `Account` | `banking/models.py` |
| `manage_authorisers_view` | `banking/views.py` |
| `add_authoriser_view` | `banking/views.py` |
| `remove_authoriser_view` | `banking/views.py` |
| `dismiss_no_authoriser_warning_view` | `banking/views.py` |
| No-authoriser banner logic in `dashboard_view` | `banking/views.py` |
| Business-branch logic in `withdraw_view`, `transfer_view`, `pay_bill_view` | `banking/views.py` |
| `pending_transactions_view` (replaced by manager dashboard) | `banking/views.py` |
| `AddAuthoriserForm` | `banking/forms.py` |
| `manage_authorisers/` URL + `add/` + `<id>/remove/` | `banking/urls.py` |
| `pending/` URL | `banking/urls.py` |
| `dashboard/dismiss-no-authoriser-warning/` URL | `banking/urls.py` |
| `manage_authorisers.html` template | `banking/templates/banking/` |

### MODIFY — adapt to new model

| Item | Change |
|------|--------|
| `Authoriser` model | Change `business_account` FK target: `Account` → `BusinessAccount`; promote from `ForeignKey` to `OneToOneField`; remove `assigned_by` field |
| `PendingTransaction` | Rename field `account` → `business_account`; change FK target: `Account` → `BusinessAccount`; drop `biller` FK (business bill payments don't use saved billers) |
| `dashboard_view` | Branch on `AccountManagerProfile` presence — render business dashboard or personal dashboard |
| `deposit_view` | Account manager path calls `deposit_to_business`; personal path unchanged |
| `withdraw_view` | Account manager path creates `PendingTransaction` for `BusinessAccount`; no authoriser-existence check (authoriser always exists); personal path unchanged |
| `transfer_view` | Same pattern as `withdraw_view` |
| `pay_bill_view` | Account manager path: bill payment form uses no saved billers (category + reference + amount); creates `PendingTransaction` for `BusinessAccount` |
| `authoriser_queue_view` | Use `request.user.authoriser_profile.business_account` (1:1) instead of queryset |
| `approve_transaction_view` | Verify `pending_tx.business_account.authoriser.user == request.user` |
| `reject_transaction_view` | Same verification pattern |
| `context_processors.authoriser_pending_count` | Rewrite: use `request.user.authoriser_profile.business_account.pending_transactions` |
| `billing_view` / `pay_bill_view` | Skip biller-save flow for account managers; bill payment form accepts category + reference + amount inline |

### ADD — new model

| Item | Location |
|------|----------|
| `BusinessAccount` model | `banking/models.py` |
| `AccountManagerProfile` model | `banking/models.py` |
| `BusinessTransaction` model | `banking/models.py` |
| `create_business_account_mock(company_name, uen, street, city, postal_code)` | `banking/services.py` |
| `deposit_to_business(biz, amount)` | `banking/services.py` |
| `approve_business_pending(pending_tx, decided_by)` | `banking/services.py` |
| `reject_business_pending(pending_tx, decided_by)` | `banking/services.py` |
| `BusinessAccountCreationForm` | `banking/forms.py` |
| `create_business_account_view` (GET + POST, public) | `banking/views.py` |
| `manager_dashboard_view` (or branched inside `dashboard_view`) | `banking/views.py` |
| `create_business_account.html` | `banking/templates/banking/` |
| `business_account_created.html` | `banking/templates/banking/` |
| `/business/create/` URL (no `@login_required`) | `banking/urls.py` |
| Migration 0009 | `banking/migrations/` |

## Key Design Decisions

### Business transaction recording
A separate `BusinessTransaction` model (parallel to personal `Transaction`) records all executed
and rejected transactions for a `BusinessAccount`. This avoids making `Transaction.account` nullable
and keeps the personal account transaction history clean.

### Bill payments for business accounts
Business account bill payments do not use the saved-biller (`Biller`) model. The account manager's
bill payment form accepts biller category, reference, and amount inline each time. This avoids
extending `Biller` with a nullable `business_account` FK.

### Phone number generation for demo accounts
Manager and authoriser users need valid Singapore mobile numbers (`^[89]\d{7}$`).
Strategy: sequential counter in the `8xxxxxxx` range. Managers receive the next odd slot
(80000001, 80000003, …); authorisers receive the next even slot (80000002, 80000004, …).
The service queries existing phone numbers before each assignment to guarantee uniqueness.

### Username uniqueness
Generated usernames follow `manager.<slug>` / `authoriser.<slug>` where `<slug>` is the
business name lowercased and stripped of non-alphanumeric characters (max 20 chars).
A numeric suffix is appended if the base username already exists.
