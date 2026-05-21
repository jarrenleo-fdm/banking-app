# Tasks: Business Account Registration

**Input**: Design documents from `specs/003-business-account/`
**Prerequisites**: plan.md ✅ spec.md ✅ research.md ✅ data-model.md ✅ contracts/views.md ✅ quickstart.md ✅

**Tests**: Included — Constitution Principle II (Test-First, NON-NEGOTIABLE) requires tests written before implementation.

**Organization**: Tasks grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on each other)
- **[Story]**: Which user story this task belongs to
- Tests MUST be written first and confirmed failing before the matching implementation tasks

---

## Phase 1: Foundational — Data Model

**Purpose**: Schema changes that ALL user stories depend on. No user story work can begin until this phase is complete.

**⚠️ CRITICAL**: Complete this phase before any Phase 2+ work.

> **Write model tests FIRST and confirm they FAIL before adding model fields**

- [x] T001 Write model tests asserting `Account.account_type` defaults to `PERSONAL`, can be set to `BUSINESS`, and is saved correctly; assert `BusinessProfile` can be created with `account`, `company_name`, and `business_registration_number`; assert `business_registration_number` unique constraint raises `IntegrityError` on duplicate in `banking/tests/test_models.py`
- [x] T002 Add `account_type` field to `Account` model (choices: PERSONAL/BUSINESS, default PERSONAL, max_length=10) in `banking/models.py` (depends on T001 failing)
- [x] T003 Add `BusinessProfile` model (OneToOne → Account, `company_name` CharField(200), `business_registration_number` CharField(20) unique, `RegexValidator(r'^[A-Za-z0-9]{6,20}$')`) in `banking/models.py` (depends on T001 failing)
- [x] T004 Generate and apply migration: `python manage.py makemigrations banking` then `python manage.py migrate` — verify `Account` table has new column and `BusinessProfile` table exists (depends on T002, T003)

**Checkpoint**: Run `pytest banking/tests/test_models.py` — all T001 model tests pass. Migration applies cleanly.

---

## Phase 2: User Story 1 — Register Business Account (Priority: P1) 🎯 MVP

**Goal**: A visitor can register a business account by selecting "Business", filling in company name and registration number, and completing the standard registration fields. The correct models are created on submission.

**Independent Test**: POST to `/accounts/signup/` with `account_type=BUSINESS`, valid personal fields, `company_name`, and a unique `business_registration_number` — expect redirect to dashboard, `BusinessProfile` row in DB, `account.account_type == BUSINESS`.

### Tests for User Story 1

> **Write these tests FIRST and confirm they FAIL before implementing**

- [x] T005 [P] [US1] Write view tests for POST `/accounts/signup/` with `account_type=BUSINESS`: (a) all valid fields → redirect to dashboard, `BusinessProfile` created, `account.account_type == BUSINESS`; (b) missing `company_name` → 200 with form error; (c) missing `business_registration_number` → 200 with form error; (d) `business_registration_number` invalid format (< 6 chars) → 200 with form error; (e) duplicate `business_registration_number` → 200 with error "This registration number is already in use." in `accounts/tests/test_views.py`
- [x] T006 [P] [US1] Write view test for POST `/accounts/signup/` with `account_type=PERSONAL` and no business fields → expect redirect to dashboard, no `BusinessProfile` created, `account.account_type == PERSONAL` in `accounts/tests/test_views.py`

### Implementation for User Story 1

- [x] T007 [US1] Add `account_type` ChoiceField (choices: PERSONAL/BUSINESS, default PERSONAL), `company_name` CharField (not required at field level), and `business_registration_number` CharField with `RegexValidator` (not required at field level) to `RegistrationForm` in `accounts/forms.py` (depends on T005, T006 failing)
- [x] T008 [US1] Add `clean()` override to `RegistrationForm` in `accounts/forms.py`: if `account_type == BUSINESS`, validate `company_name` is non-blank and `business_registration_number` is provided and unique (query `BusinessProfile.objects.filter(business_registration_number=...)`) (depends on T007)
- [x] T009 [US1] Update `signup_view` in `accounts/views.py`: after `form.save()` and account signal, if `account_type == BUSINESS` → `account.account_type = BUSINESS`, `account.save(update_fields=["account_type"])`, `BusinessProfile.objects.create(account=account, company_name=..., business_registration_number=...)` (depends on T007, T008)

**Checkpoint**: Run `pytest accounts/tests/test_views.py` — all T005 and T006 tests pass. Business account registration creates the correct DB records.

---

## Phase 3: User Story 2 — Account Type Label on Dashboard (Priority: P2)

**Goal**: Logged-in users see their account type ("Personal" or "Business") clearly labelled on the dashboard.

**Independent Test**: Log in as a business account user, visit `/banking/dashboard/` — response HTML must contain "Business". Log in as a personal account user — response must contain "Personal".

### Tests for User Story 2

> **Write these tests FIRST and confirm they FAIL before implementing**

- [x] T010 [P] [US2] Write view tests for GET `/banking/dashboard/`: (a) business account user → response contains "Business"; (b) personal account user → response contains "Personal" in `banking/tests/test_views.py`

### Implementation for User Story 2

- [x] T011 [US2] Add account type label (e.g. a badge or text element showing `account.get_account_type_display()`) to `banking/templates/banking/dashboard.html` (depends on T010 failing)

**Checkpoint**: Run `pytest banking/tests/test_views.py -k dashboard` — T010 tests pass. Dashboard shows the correct label for both account types.

---

## Phase 4: User Story 3 — Account Type Toggle at Sign-Up (Priority: P3)

**Goal**: The sign-up page presents a clear "Personal" / "Business" selector. Selecting "Business" reveals the business fields without a page reload; switching back hides them.

**Independent Test**: Load `/accounts/signup/` in a browser. Confirm "Personal" is selected and business fields are hidden. Select "Business" — company name and registration number fields appear. Switch back — they disappear. No page reload occurs.

### Implementation for User Story 3

- [x] T012 [US3] Update `accounts/templates/accounts/signup.html`: add radio button group for account type (Personal / Business, Personal selected by default); wrap `company_name` and `business_registration_number` fields in a `<div id="business-fields">` hidden by default; add inline `<script>` that toggles `business-fields` visibility on radio button `change` event (depends on T007 — form fields must exist to render)

**Checkpoint**: Load sign-up page in browser. Toggle between Personal and Business — business fields appear and disappear correctly. Submit a business account form — fields are present and submitted.

---

## Phase 5: Polish & Cross-Cutting Concerns

- [x] T013 Run full test suite and confirm all tests pass: `pytest --cov=accounts --cov=banking --cov-report=term-missing`
- [x] T014 [P] Run pre-commit hooks across all changed files: `pre-commit run --files accounts/forms.py accounts/views.py banking/models.py banking/templates/banking/dashboard.html accounts/templates/accounts/signup.html`
- [x] T015 Follow `specs/003-business-account/quickstart.md` — verify business account registration, validation errors, and personal account behaviour end-to-end in the browser

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Foundational)**: No dependencies — start here. BLOCKS all other phases.
- **Phase 2 (US1)**: Depends on Phase 1 completion.
- **Phase 3 (US2)**: Depends on Phase 1 completion. Can run in parallel with Phase 2 (different files).
- **Phase 4 (US3)**: Depends on Phase 2 (T007 — form fields must exist to render in template). Cannot start until T007 is done.
- **Phase 5 (Polish)**: Depends on all user story phases.

### User Story Dependencies

- **US1 (P1)**: Depends on Phase 1. Independent of US2 and US3.
- **US2 (P2)**: Depends on Phase 1 (`account_type` field must exist on `Account`). Independent of US1 implementation.
- **US3 (P3)**: Depends on US1 form fields (T007) being present to render in the template.

### Within Each Phase

- Tests MUST be written and confirmed failing before implementation tasks in the same phase.
- T002 and T003 can run in parallel (both modify `banking/models.py` sequentially, but can be done in one edit pass).
- T005 and T006 can run in parallel (both add tests to `accounts/tests/test_views.py`).
- T010 can start as soon as Phase 1 is complete (no dependency on Phase 2).

### Parallel Opportunities

```bash
# Once Phase 1 is complete, these can proceed in parallel:
Phase 2 (US1): accounts/forms.py, accounts/views.py, accounts/tests/test_views.py
Phase 3 (US2): banking/templates/banking/dashboard.html, banking/tests/test_views.py
```

---

## Implementation Strategy

### MVP First (User Stories 1 + 2)

1. Complete Phase 1: Foundational (data model + migration)
2. Complete Phase 2: US1 (business registration form + view)
3. Complete Phase 3: US2 (dashboard label)
4. **STOP and VALIDATE**: Business users can register and see their account type — core feature complete.

### Full Delivery

5. Complete Phase 4: US3 (JS toggle UX polish)
6. Complete Phase 5: Polish + quickstart verification

---

## Notes

- [P] tasks = operate on different files, no outstanding task dependencies
- Each checkpoint is a meaningful, independently testable increment
- The `account_type` field uses `get_account_type_display()` in templates for human-readable labels
- Pre-commit hooks (flake8, pylint, bandit) must pass before each commit per Prototype tier compensating controls
- No new Python dependencies required
