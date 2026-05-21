# Tasks: Billing System — Mandatory & Unique Reference Amendment

**Input**: Design documents from `specs/004-billing-system/`
**Prerequisites**: plan.md ✅, spec.md ✅ (clarified 2026-05-21), data-model.md ✅, contracts/endpoints.md ✅

**Scope**: This tasks file covers the mandatory+unique reference amendment. The predefined-categories amendment (original T001–T007) is complete. This plan finalises the feature by enforcing a mandatory, per-user-per-category-unique `reference` field on `Biller`, updating the form, views, service, template, and all affected tests.

**Tests**: Included. Constitution Principle II (Test-First) is NON-NEGOTIABLE — all test tasks must be written and confirmed FAILING before the corresponding implementation task is considered done.

---

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no blocking dependencies)
- **[Story]**: Maps to user story from spec.md (US1 = Pay a Bill, US2 = Manage Saved Billers, US3 = View Bill Payment History)

---

## Phase 1: Setup

**Purpose**: Confirm the baseline is healthy before any changes.

- [x] T001 Run full test suite to confirm zero failures before amendment: `python3 -m pytest -q`

---

## Phase 2: Foundational — Model + Migration (Blocking Prerequisites)

**Purpose**: The `unique_together` constraint, mandatory `reference`, and updated `__str__` must land in the database before the form or service can rely on them.

**⚠️ CRITICAL**: T002–T004 must complete before Phase 3 and Phase 4 begin.

> **NOTE: Write tests first (T002) and confirm they FAIL before implementing T003.**

- [x] T002 Write failing model tests in `banking/tests/test_models.py`: (a) update `test_biller_str_returns_name` — expect `"Electricity (ACC-001)"` not `"Electricity"`; (b) replace `test_biller_reference_can_be_blank` with `test_biller_reference_is_mandatory` — saving a Biller with `reference=""` raises `ValidationError`; (c) add `test_biller_categories_all_return_correct_display_labels` — update any fixture creating a Biller without a reference to include `reference="REF-001"`; (d) add `test_biller_reference_unique_per_account_and_category` — creating two Billers with the same account+name+reference raises `IntegrityError`; (e) add `test_biller_same_reference_allowed_across_categories` — same reference under different categories for the same account succeeds
- [x] T003 Update `Biller` in `banking/models.py`: (a) remove `blank=True` from `reference = models.CharField(max_length=100)`; (b) add `class Meta: unique_together = [("account", "name", "reference")]`; (c) update `__str__` to `return f"{self.get_name_display()} ({self.reference})"`
- [x] T004 Generate migration `banking/migrations/0005_biller_reference_mandatory_unique.py`: `python3 manage.py makemigrations banking --name biller_reference_mandatory_unique` — verify it contains `AlterField` (removes `blank=True`) and `AlterUniqueTogether` (adds the constraint), then apply: `python3 manage.py migrate`

**Checkpoint**: `python3 -m pytest banking/tests/test_models.py -q` — all model tests pass; `python3 manage.py shell -c "from banking.models import Biller; b = Biller(); print(b._meta.unique_together)"` prints `[('account', 'name', 'reference')]`.

---

## Phase 3: User Story 2 — Mandatory Reference in Add-Biller Form (Priority: P2)

**Goal**: The add-biller form rejects blank references and duplicate (account + category + reference) combinations with clear error messages.

**Independent Test**: `POST /banking/billing/biller/add/` with a blank `reference` returns HTTP 200 with a form error; with a duplicate category+reference returns HTTP 200 with a non-field form error; with a valid category and reference redirects to `banking:billing`.

> **NOTE: Write tests first (T005) and confirm they FAIL before implementing T006–T008.**

- [x] T005 Write failing view tests in `banking/tests/test_views.py`: (a) `test_add_biller_view_rejects_blank_reference` — POST with `name="ELECTRICITY"` and `reference=""` returns HTTP 200 and contains a reference field error; (b) `test_add_biller_view_rejects_duplicate_reference` — after creating a Biller(account, name="ELECTRICITY", reference="ACC-001"), POST with the same name+reference returns HTTP 200 and contains a non-field form error "A biller with this category and reference already exists."
- [x] T006 [P] [US2] Update `BillerForm` in `banking/forms.py`: (a) change `reference = forms.CharField(max_length=100, required=False)` to `required=True` (drop the `required=False`); (b) add `__init__(self, *args, account=None, **kwargs)` storing `self.account = account`; (c) add `clean()` that checks `Biller.objects.filter(account=self.account, name=name, reference=reference).exists()` and raises `forms.ValidationError("A biller with this category and reference already exists.")` if true
- [x] T007 [P] [US2] Update `add_biller_view` in `banking/views.py`: change `BillerForm(request.POST)` to `BillerForm(request.POST, account=account)`; change `form.cleaned_data.get("reference", "")` to `form.cleaned_data["reference"]`
- [x] T008 [US2] Update `banking/templates/banking/billing.html`: add `required` attribute to the reference `<input>` field in the add-biller form

**Checkpoint**: `python3 -m pytest banking/tests/test_views.py -q` — all view tests pass; manual smoke test: submit add-biller form without reference → form error shown, no biller created; submit with duplicate category+reference → non-field error shown.

---

## Phase 4: User Story 1 — Service Description Includes Reference (Priority: P1)

**Goal**: The `pay_bill` transaction record stores `"{category} ({reference})"` so the audit trail remains self-contained even after a biller is deleted.

**Independent Test**: After paying a bill, `Transaction.objects.filter(transaction_type="BILL_PAYMENT").last().description` equals `"Internet & Broadband (ACC-001)"` (not just `"Internet & Broadband"`).

> **NOTE: Write test first (T009) and confirm it FAILS before implementing T010.**

- [x] T009 [US1] Update `test_pay_bill_stores_biller_name_in_description` in `banking/tests/test_services.py`: change the assertion from `assert txn.description == "Internet & Broadband"` to `assert txn.description == "Internet & Broadband (ACC-001)"` — confirm the test now fails before T010 is implemented
- [x] T010 [US1] Update `pay_bill` in `banking/services.py`: change `description=biller.get_name_display()` to `description=f"{biller.get_name_display()} ({biller.reference})"`

**Checkpoint**: `python3 -m pytest banking/tests/test_services.py -q` — all service tests pass.

---

## Phase 5: Polish & Cross-Cutting Concerns

**Purpose**: Confirm zero regressions and linting remains clean across all changed files.

- [x] T011 Run full test suite and confirm zero failures: `python3 -m pytest -q`
- [x] T012 [P] Run flake8 and confirm clean exit: `flake8 banking/ --max-line-length=100`
- [x] T013 [P] Run pylint and confirm no new errors: `pylint banking/models.py banking/forms.py banking/services.py banking/views.py`
- [x] T014 [P] Run bandit security scan: `bandit -r banking/`
- [ ] T015 Run quickstart.md smoke test manually: follow steps 1–7 in `specs/004-billing-system/quickstart.md` to confirm end-to-end behaviour

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 passing — **BLOCKS Phases 3 and 4**
- **User Story 2 (Phase 3)**: Depends on Phase 2 (model + migration must be applied before BillerForm can use `unique_together` backstop)
- **User Story 1 (Phase 4)**: Depends on Phase 2 (model `__str__` must be updated before service description relies on `biller.reference`)
  - Phase 3 and Phase 4 can proceed in parallel once Phase 2 is complete
- **Polish (Phase 5)**: Depends on Phases 3 and 4 complete

### Within Each Phase (Red-Green-Refactor)

```
Phase 2: T002 (write tests, confirm FAIL) → T003 (implement model) → T004 (migrate)
Phase 3: T005 (write tests, confirm FAIL) → T006 + T007 (implement form+view, parallel) → T008 (template)
Phase 4: T009 (write test, confirm FAIL) → T010 (implement service)
Phase 5: T011 → T012 + T013 + T014 (parallel) → T015
```

### Parallel Opportunities

- T006 (forms.py) and T007 (views.py) target different files — safe to work in parallel after T005 passes
- T012, T013, T014 (linting tools) are fully independent — run together
- Phase 3 and Phase 4 can be worked in parallel by different developers once Phase 2 is complete

---

## Parallel Example: Phase 3

```text
# Step 1 — Write tests, confirm they fail:
T005: Write blank-reference + duplicate-reference tests in banking/tests/test_views.py

# Step 2 — Implement (different files, can run in parallel):
T006: Update BillerForm in banking/forms.py
T007: Update add_biller_view in banking/views.py

# Step 3 — Template:
T008: Add required attribute to reference input in banking/templates/banking/billing.html

# Step 4 — Verify:
Run: python3 -m pytest banking/tests/test_views.py -q
```

---

## Implementation Strategy

### Full Amendment (all phases)

1. Phase 1: Baseline check — confirm zero failures before touching anything
2. Phase 2: Model + Migration — foundational, blocks everything; test-first
3. Phase 3: Form + View + Template — user-facing enforcement; test-first
4. Phase 4: Service description — audit trail fix; test-first
5. Phase 5: Full suite + linting + manual smoke test

Total: **15 tasks** across 5 phases.

---

## Notes

- [P] = different files, no blocking dependency — safe to parallelise
- Test tasks (T002, T005, T009) must be written and confirmed **FAILING** before the matching implementation tasks are considered complete — this is Constitution Principle II; skipping it is not permitted
- The `unique_together` DB constraint is the hard backstop; `BillerForm.clean()` is the user-friendly layer — both are required (Principle V — Data Integrity)
- `Biller.__str__` change affects the `BillPaymentForm` dropdown labels automatically (ModelChoiceField uses `str(instance)`) — no per-form override needed
- `BillerForm.clean()` must guard against `self.account is None` (e.g., in unit tests that don't pass an account) — skip the uniqueness check if `account` is None
- Migration 0005 must not drop or recreate the column — verify `makemigrations` output contains `AlterField` + `AlterUniqueTogether`, not `DeleteField`/`CreateField`
