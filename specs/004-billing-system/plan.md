# Implementation Plan: Billing System

**Branch**: `004-billing-system` | **Date**: 2026-05-21 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/004-billing-system/spec.md`

## Summary

Add a billing system allowing users to save billers (from 5 fixed categories), pay bills from saved billers, and view payment history. The billing infrastructure (model scaffolding, service skeleton, views, and URL routes) was already partially implemented on this branch. This plan finalises the feature by enforcing a **mandatory, per-user-per-category-unique reference field** on the `Biller` model, updating all related forms, tests, service descriptions, and adding the migration. All changes are surgical — no new architectural layers are introduced.

## Technical Context

**Language/Version**: Python 3.x · Django 5.2 (LTS)
**Primary Dependencies**: Django 5.2, django-environ, gunicorn; pytest + pytest-django (test runner)
**Storage**: SQLite3 — Prototype tier; `@transaction.atomic` provides exclusive write lock (no `select_for_update` required)
**Testing**: pytest via `pytest.ini`; test files in `banking/tests/` (`test_models.py`, `test_services.py`, `test_views.py`)
**Target Platform**: Django web application; server-rendered HTML with form POST patterns
**Project Type**: Django web service (monolith — `accounts` + `banking` apps)
**Performance Goals**: Users complete a bill payment in under 2 minutes (SC-001)
**Constraints**: Prototype/Learning tier; SQLite3 concurrency handled by `@transaction.atomic`
**Scale/Scope**: Single account per user; billers are private per user

## Constitution Check

**Active Tier: Prototype / Learning**

*GATE: Must pass before implementation starts.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I — Security | ✅ PASS | All billing views are `@login_required`; biller ownership enforced in every view (`account=account` filter or `get_object_or_404`); CSRF active; no sensitive data in error messages |
| II — Test-First | ✅ PASS | Tests written before implementation per Red-Green-Refactor; every money path has unit + integration tests |
| III — SonarQube | ✅ PASS (tier) | Prototype tier — SonarQube not required; compensating controls: `flake8`, `pylint`, `bandit` run locally before each commit |
| IV — Auditability | ✅ PASS | `pay_bill` creates an immutable `Transaction` record with description including biller category + reference |
| V — Data Integrity | ✅ PASS (tier) | `@transaction.atomic` on `pay_bill`; SQLite3 exclusive lock satisfies Prototype tier; Decimal for all monetary values |

**No violations requiring Complexity Tracking.** Prototype-tier relaxations (SonarQube, `select_for_update`) are pre-approved in the constitution and recorded in `specs/001-core-banking-operations/plan.md`.

## Project Structure

### Documentation (this feature)

```text
specs/004-billing-system/
├── plan.md              ← this file
├── research.md          ← Phase 0 output
├── data-model.md        ← Phase 1 output
├── quickstart.md        ← Phase 1 output
├── contracts/
│   └── billing-endpoints.md  ← Phase 1 output
└── tasks.md             ← Phase 2 output (/speckit-tasks)
```

### Source Code (repository root)

```text
banking/
├── models.py            ← Biller: remove blank=True on reference, add unique_together, update __str__
├── forms.py             ← BillerForm: reference required=True, add account param + clean() for uniqueness
├── services.py          ← pay_bill: include reference in transaction description
├── views.py             ← add_biller_view: pass account to BillerForm
├── migrations/
│   └── 0005_biller_reference_mandatory_unique.py  ← new migration
├── templates/banking/
│   └── billing.html     ← mark reference input as required
└── tests/
    ├── test_models.py   ← update Biller __str__ tests; replace blank-reference test; add uniqueness tests
    ├── test_services.py ← update description assertion to include reference
    └── test_views.py    ← add blank-reference rejection test; add duplicate-reference rejection test
```

**Structure Decision**: Single Django app (`banking`); all billing code lives within this existing app. No new files outside migrations and the spec artifacts above.
