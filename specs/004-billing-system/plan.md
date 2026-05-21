# Implementation Plan: Billing System

**Branch**: `004-billing-system` | **Date**: 2026-05-21 | **Spec**: [spec.md](spec.md)  
**Input**: Feature specification from `specs/004-billing-system/spec.md`

## Summary

Allow logged-in users to save billers by selecting from five predefined categories (Electricity, Water & Utilities, Internet & Broadband, Telecommunications, Town Council / Maintenance) and pay bills directly from their account balance. Bill payments are atomic balance deductions recorded as a `BILL_PAYMENT` transaction type, appearing in the existing transaction history. The feature is implemented entirely within the existing `banking` Django app.

**Amendment (2026-05-21):** The original plan specified free-text biller names. Following `/speckit-clarify`, biller names are now constrained to five predefined categories stored as Django model choices. This changes `Biller.name` from a free-text `CharField` to a `CharField(choices=BILLER_CATEGORIES)`, and `BillerForm.name` from a `CharField` to a `ChoiceField`. A new migration is required.

## Technical Context

**Language/Version**: Python 3.11  
**Primary Dependencies**: Django (LTS), Django ORM  
**Storage**: SQLite3 (Prototype/Learning tier)  
**Testing**: pytest-django (existing project convention)  
**Target Platform**: Local web server (Django dev server)  
**Project Type**: Web application (Django, server-rendered templates)  
**Performance Goals**: Standard web app — page loads under 2 seconds  
**Constraints**: No floating-point money; all balance operations atomic; user data isolation enforced at query level  
**Scale/Scope**: Single-user-per-account model; Prototype tier  
**Deployment Tier**: **Prototype / Learning**

## Constitution Check

*GATE: Must pass before implementation begins.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Security (NON-NEGOTIABLE) | ✅ PASS | All billing views use `@login_required`; biller ownership enforced by scoping all queries to `request.user.account`; no biller or payment data accessible across users |
| II. Test-First (NON-NEGOTIABLE) | ✅ PASS | Red-Green-Refactor cycle required; tests for updated `BillerForm` and biller category choices written before implementation |
| III. SonarQube | ⚠ RELAXED | Prototype/Learning tier; compensated by `flake8`, `pylint`, and `bandit` |
| IV. Auditability | ✅ PASS | Bill payments create immutable `Transaction` records with category name in description |
| V. Data Integrity | ✅ PASS (with relaxation) | `pay_bill` wrapped in `@transaction.atomic`; `select_for_update()` not required on SQLite3 |

## Project Structure

### Documentation (this feature)

```text
specs/004-billing-system/
├── plan.md              # This file
├── research.md          # Phase 0 output (updated for predefined categories)
├── data-model.md        # Phase 1 output (updated: Biller.name → choices)
├── quickstart.md        # Phase 1 output
├── contracts/
│   └── endpoints.md     # Phase 1 output (updated: add_biller uses dropdown)
└── tasks.md             # Phase 2 output (/speckit-tasks)
```

### Source Code

```text
banking/
├── models.py               ← amend Biller: add BILLER_CATEGORIES choices, constrain name field
├── forms.py                ← amend BillerForm: name becomes ChoiceField
├── migrations/
│   └── 0004_biller_name_choices.py  ← new (choices-only, no schema change)
└── tests/
    ├── test_models.py      ← add choices validation tests for Biller
    └── test_views.py       ← add test: add_biller with invalid category is rejected
```

No changes required to `services.py`, `views.py`, `urls.py`, or templates — the category constraint is enforced at the form and model level only.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|--------------------------------------|
| Principle III — no SonarQube CI | Prototype/Learning tier | Setting up SonarQube CI is out of scope; `flake8 + pylint + bandit` run locally |
| Principle V — no `select_for_update()` | SQLite3 backend | `@transaction.atomic` on SQLite3 issues exclusive write lock |

**Production migration TODO**: Before involving real users or real money, migrate to PostgreSQL, enable `select_for_update()` in `pay_bill`, integrate SonarQube CI, and re-declare as Production tier.
