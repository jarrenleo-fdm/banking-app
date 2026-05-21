# Tasks: Billing System — Predefined Biller Categories Amendment

**Input**: Design documents from `specs/004-billing-system/` (post-clarification update)
**Prerequisites**: plan.md ✅, spec.md ✅ (clarified 2026-05-21), data-model.md ✅, contracts/endpoints.md ✅

**Scope**: This tasks file covers only the predefined-categories amendment. The original billing system implementation (T001–T026 from the prior tasks run) is complete. Only `banking/models.py`, `banking/forms.py`, and a new migration require changes.

**Tests**: Included. Constitution Principle II (Test-First) is NON-NEGOTIABLE for model-level validation changes.

---

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no blocking dependencies)
- **[Story]**: Maps to the user story from spec.md affected by each task

---

## Phase 1: Setup

**Purpose**: Confirm the baseline is healthy before any changes.

- [ ] T001 Run full test suite to confirm zero failures before amendment: `python3 -m pytest -q`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Model and schema changes that must land before the form can reference the new constants.

**⚠️ CRITICAL**: T003 must complete before T004–T005.

- [ ] T002 Add `BILLER_CATEGORIES` constant and five category tuples (`ELECTRICITY`, `WATER_UTILITIES`, `INTERNET_BROADBAND`, `TELECOMMUNICATIONS`, `TOWN_COUNCIL`) to `Biller` in `banking/models.py`; change `Biller.name` from `CharField(max_length=100)` to `CharField(max_length=50, choices=BILLER_CATEGORIES)`
- [ ] T003 Generate and apply migration `banking/migrations/0004_biller_name_choices.py`: `python3 manage.py makemigrations banking --name biller_name_choices && python3 manage.py migrate`

**Checkpoint**: `python3 manage.py shell -c "from banking.models import Biller; print(Biller.BILLER_CATEGORIES)"` prints the five tuples.

---

## Phase 3: User Story 2 Amendment — Predefined Biller Categories (Priority: P2)

**Goal**: When adding a biller, users select a category from a `<select>` dropdown rather than typing a free-text name. Invalid categories are rejected at the form and model level.

**Independent Test**: `POST /banking/billing/biller/add/` with `name="ELECTRICITY"` creates a Biller; the same POST with `name="Fake Biller"` returns HTTP 200 with a form error.

> **NOTE: Write tests FIRST (T004) and confirm they FAIL before implementing T005.**

- [ ] T004 [US2] Write failing tests: (a) in `banking/tests/test_models.py` — Biller with a valid category value saves correctly, `Biller.__str__` returns the display label; (b) in `banking/tests/test_views.py` — `add_biller_view` accepts a valid category (`ELECTRICITY`) and redirects, rejects an invalid category string and returns HTTP 200 with a form error
- [ ] T005 [P] [US2] Update `BillerForm.name` in `banking/forms.py`: replace `CharField(max_length=100)` with `ChoiceField(choices=Biller.BILLER_CATEGORIES)` and remove the whitespace-strip `clean_name` method (no longer needed — the field validates against the fixed choice list automatically)

**Checkpoint**: All new tests pass; `GET /banking/billing/` renders the add-biller form with a `<select>` for the name field.

---

## Phase 4: Polish

**Purpose**: Confirm zero regressions and linting remains clean.

- [ ] T006 Run full test suite and confirm zero failures: `python3 -m pytest -q`
- [ ] T007 [P] Run flake8 and confirm clean exit: `flake8 banking/ --max-line-length=100`

---

## Dependencies & Execution Order

- **Phase 1**: No dependencies — start immediately
- **Phase 2**: Depends on Phase 1 passing — BLOCKS Phase 3
- **Phase 3**: Depends on Phase 2 (model constants must exist for `BillerForm` to reference `Biller.BILLER_CATEGORIES`)
  - T004 (tests) and T005 (form) can run in parallel after T003 completes — different files
- **Phase 4**: Depends on Phase 3 complete

### Within Phase 3

- T004 (tests) written first — confirm they FAIL
- T005 (form update) implemented — confirm tests now PASS

### Parallel Opportunities

- T004 and T005 target different files (`test_models.py` + `test_views.py` vs `forms.py`) — safe to work in parallel if two developers, but T004 must be written and confirmed failing before T005 is considered done
- T006 and T007 in Phase 4 are independent

---

## Parallel Example: Phase 3

```text
# Step 1 — Write tests first (confirm they fail):
T004: Write Biller category tests in banking/tests/test_models.py
      Write add_biller category validation tests in banking/tests/test_views.py

# Step 2 — Implement (different file, can overlap with writing T004):
T005: Update BillerForm.name to ChoiceField in banking/forms.py

# Step 3 — Verify:
Run: python3 -m pytest banking/tests/ -q
```

---

## Implementation Strategy

### Full Amendment (all phases)

1. Phase 1: Baseline check
2. Phase 2: Model + migration
3. Phase 3: Tests → Form update → Verify
4. Phase 4: Full suite + linting

Total: **7 tasks** across 4 phases.

---

## Notes

- [P] = different files, no blocking dependency — safe to parallelise
- `BillerForm.clean_name()` is removed — `ChoiceField` handles validation automatically; no custom cleaner needed
- `Biller.__str__` should use `get_name_display()` to return the human-readable label (e.g., "Electricity") rather than the stored key (e.g., "ELECTRICITY")
- The migration is a schema change (`max_length` reduction); confirm it generates as `AlterField`, not a destructive operation
- Existing test fixture billers created with raw strings (e.g., `name="SP PowerGrid"`) will break once the migration is applied — update fixtures to use `Biller.ELECTRICITY` constants
