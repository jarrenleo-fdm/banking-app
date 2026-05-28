# Tasks: UX Enhancements

**Input**: Design documents from `specs/002-ux-enhancements/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/services.md, contracts/views.md, quickstart.md

**Tests**: Included because the project constitution requires test-first development.

**Organization**: Tasks are grouped by user story so each story can be implemented and tested independently.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel when it touches different files and has no dependency on incomplete tasks.
- **[Story]**: Maps to a user story in `specs/002-ux-enhancements/spec.md`.
- Tests must be written first and confirmed failing before implementing the matching story.

---

## Phase 1: Setup

**Purpose**: Confirm the refreshed UX plan is ready for implementation and that no schema work is expected.

- [X] T001 Review active feature artifacts in `specs/002-ux-enhancements/spec.md`, `specs/002-ux-enhancements/plan.md`, `specs/002-ux-enhancements/data-model.md`, and `specs/002-ux-enhancements/contracts/views.md`
- [X] T002 Verify no model migrations are needed by running `python manage.py makemigrations --check` against `accounts/models.py` and `banking/models.py`
- [X] T003 Review existing route, form, and template patterns in `accounts/urls.py`, `accounts/forms.py`, `accounts/views.py`, `templates/base.html`, and `banking/templates/banking/transactions.html`

---

## Phase 2: Foundational

**Purpose**: Shared constraints that must be respected by all story work.

- [X] T004 Confirm password, phone-number, Decimal money, and immutable transaction conventions in `AGENTS.md` and `specs/002-ux-enhancements/research.md`
- [X] T005 Confirm test-first coverage targets and local quality commands in `pytest.ini`, `requirements-dev.txt`, and `.pre-commit-config.yaml`

**Checkpoint**: User story implementation can begin after setup and foundational review are complete.

---

## Phase 3: User Story 1 - Password Criteria Guidance (Priority: P1) MVP

**Goal**: Users see real-time password criteria on signup and password reset forms, and the backend enforces the same rules.

**Independent Test**: Navigate to `/accounts/signup/`, type a password missing one criterion, submit it, and confirm the form rejects it while the criteria checklist reflects the unmet rule.

### Tests for User Story 1

- [X] T006 [P] [US1] Add validator unit tests for `PasswordComplexityValidator.validate()` and `get_help_text()` in `accounts/tests/test_validators.py`
- [X] T007 [P] [US1] Add signup and password-reset view tests for weak-password rejection in `accounts/tests/test_views.py`

### Implementation for User Story 1

- [X] T008 [US1] Implement `PasswordComplexityValidator` character-class checks in `accounts/validators.py`
- [X] T009 [US1] Register `accounts.validators.PasswordComplexityValidator` in `banking_app/settings.py`
- [X] T010 [US1] Implement real-time criteria behavior for password fields in `static/js/password-criteria.js`
- [X] T011 [P] [US1] Add criteria checklist markup and script reference to `accounts/templates/accounts/signup.html`
- [X] T012 [P] [US1] Add criteria checklist markup and script reference to `accounts/templates/accounts/password_reset_confirm.html`
- [X] T013 [US1] Run focused password tests with `pytest accounts/tests/test_validators.py accounts/tests/test_views.py -v`

**Checkpoint**: Signup and password reset both reject weak passwords and show matching criteria guidance.

---

## Phase 4: User Story 2 - Transfer Party Visibility in Transaction History (Priority: P1)

**Goal**: Transfer rows show whether the counterparty is the sender or recipient.

**Independent Test**: Perform a transfer between two accounts and confirm sender history shows "To:" while recipient history shows "From:".

### Tests for User Story 2

- [X] T014 [US2] Add transaction-history view tests for `TRANSFER_OUT` "To:" and `TRANSFER_IN` "From:" labels in `banking/tests/test_views.py`

### Implementation for User Story 2

- [X] T015 [US2] Ensure transaction history query exposes counterparty account/user data in `banking/views.py`
- [X] T016 [US2] Render directional counterparty labels in `banking/templates/banking/transactions.html`
- [X] T017 [US2] Run focused history tests with `pytest banking/tests/test_views.py -v`

**Checkpoint**: Transfer history entries show the correct directional counterparty label.

---

## Phase 5: User Story 3 - Transaction ID in History (Priority: P2)

**Goal**: Every transaction row displays a unique transaction ID for support and audit reference.

**Independent Test**: View transaction history and confirm every row shows a non-empty transaction ID and different transactions have different IDs.

### Tests for User Story 3

- [X] T018 [US3] Add transaction-history view tests for visible unique transaction IDs in `banking/tests/test_views.py`

### Implementation for User Story 3

- [X] T019 [US3] Add a transaction ID column or label to `banking/templates/banking/transactions.html`
- [X] T020 [US3] Run focused transaction ID tests with `pytest banking/tests/test_views.py -v`

**Checkpoint**: All transaction history entries expose their unique transaction ID.

---

## Phase 6: User Story 4 - Transfer Description (Priority: P2)

**Goal**: Users can add an optional transfer description, and it appears in both sender and recipient histories.

**Independent Test**: Send a transfer with description "Rent May" and confirm it appears on both sides; send one without a description and confirm no empty label appears.

### Tests for User Story 4

- [X] T021 [P] [US4] Add service tests for description propagation to both transfer records in `banking/tests/test_services.py`
- [X] T022 [P] [US4] Add transfer form, view, and history display tests for descriptions in `banking/tests/test_views.py`

### Implementation for User Story 4

- [X] T023 [P] [US4] Add optional `description` parameter handling to `transfer()` in `banking/services.py`
- [X] T024 [P] [US4] Add optional `description` field with 200 character limit to `TransferForm` in `banking/forms.py`
- [X] T025 [US4] Pass cleaned transfer descriptions from the transfer view to the service in `banking/views.py`
- [X] T026 [US4] Add the transfer description input to `banking/templates/banking/dashboard.html`
- [X] T027 [US4] Render non-empty transfer descriptions in `banking/templates/banking/transactions.html`
- [X] T028 [US4] Run focused transfer tests with `pytest banking/tests/test_services.py banking/tests/test_views.py -v`

**Checkpoint**: Transfer descriptions flow from form to service to both immutable transaction records and both history views.

---

## Phase 7: User Story 6 - Update User Details and Credentials (Priority: P2)

**Goal**: Authenticated users can update name, username, email address, phone number, and password from the signed-in profile experience.

**Independent Test**: Log in, update valid profile details and credentials, confirm they are saved immediately, then verify duplicate or invalid username/email/phone submissions and invalid password-change submissions are rejected without changing saved details or password.

### Tests for User Story 6

- [X] T029 [P] [US6] Add form tests for valid contact update, blank name, duplicate email, duplicate phone, and invalid phone in `accounts/tests/test_forms.py`
- [X] T030 [P] [US6] Add form tests for valid username update, duplicate username, invalid username, and unchanged username in `accounts/tests/test_forms.py`
- [X] T031 [P] [US6] Add view tests for username-change success and duplicate/invalid username rejection in `accounts/tests/test_views.py`
- [X] T032 [P] [US6] Add view tests for password-change success, session preservation, old-password rejection, wrong current password, weak new password, and mismatched confirmation in `accounts/tests/test_views.py`
- [X] T033 [P] [US6] Add authenticated profile GET/POST, anonymous redirect, success message, and invalid contact submission view tests in `accounts/tests/test_views.py`
- [X] T034 [P] [US6] Add regression test that transfer lookup uses an updated phone number in `banking/tests/test_views.py`

### Implementation for User Story 6

- [X] T035 [US6] Create `UserDetailsForm` with current-user-aware email and phone validation in `accounts/forms.py`
- [X] T036 [US6] Extend `UserDetailsForm` with editable username format and uniqueness validation in `accounts/forms.py`
- [X] T037 [US6] Add authenticated password-change handling with current-password validation, session preservation, success/error messages, and non-PII credential logging in `accounts/views.py`
- [X] T038 [US6] Add `/accounts/profile/` route named `profile` in `accounts/urls.py`
- [X] T039 [US6] Update user details template with editable username fields, password-change fields, and criteria guidance in `accounts/templates/accounts/profile.html`
- [X] T040 [US6] Add signed-in navigation to the profile page in `templates/base.html`
- [X] T041 [US6] Run focused profile credential tests with `pytest accounts/tests/test_forms.py accounts/tests/test_views.py banking/tests/test_views.py -v`

**Checkpoint**: Users can self-service update contact details, username, and password; future login and phone-based transfer flows use the updated values.

---

## Phase 8: User Story 5 - Optional Initial Balance on Registration (Priority: P3)

**Goal**: Signup accepts an optional non-negative initial balance, defaulting to zero when blank.

**Independent Test**: Register with `500.00` and confirm the dashboard balance/history reflect it; register blank or zero and confirm zero balance; submit a negative value and confirm rejection.

### Tests for User Story 5

- [X] T042 [US5] Add signup view tests for positive, blank, explicit zero, negative, and non-numeric initial balance cases in `accounts/tests/test_views.py`

### Implementation for User Story 5

- [X] T043 [US5] Add optional non-negative `initial_balance` DecimalField validation to `RegistrationForm` in `accounts/forms.py`
- [X] T044 [US5] Apply positive signup initial balances through the existing `deposit()` service in `accounts/views.py`
- [X] T045 [US5] Ensure signup template displays the initial balance field in `accounts/templates/accounts/signup.html`
- [X] T046 [US5] Run focused signup balance tests with `pytest accounts/tests/test_views.py -v`

**Checkpoint**: Registration supports optional initial balance while preserving balance and transaction-history reconciliation.

---

## Phase 9: Polish & Cross-Cutting Concerns

**Purpose**: Verify the full feature and clean up any cross-story regressions.

- [X] T047 [P] Update UX feature notes if implementation changes assumptions in `specs/002-ux-enhancements/quickstart.md`
- [X] T048 [P] Run account and banking tests with `pytest accounts/tests/ banking/tests/ -v`
- [X] T049 [P] Run coverage check with `pytest --cov=accounts --cov=banking --cov-report=term-missing`
- [ ] T050 Run static analysis with `pre-commit run --all-files` using `.pre-commit-config.yaml`
- [ ] T051 Manually verify all six stories using `specs/002-ux-enhancements/quickstart.md`

**T050 note**: Attempted on 2026-05-28. `flake8`/`pylint` still fail on pre-existing unrelated `banking/` and `mcp_server/tests/test_auth.py` issues; touched account files pass `flake8`, `bandit`, and direct `pylint`.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies; start immediately.
- **Phase 2 (Foundational)**: Depends on Phase 1; complete before user-story edits.
- **Phase 3 (US1)**: Depends on Phase 2.
- **Phase 4 (US2)**: Depends on Phase 2.
- **Phase 5 (US3)**: Depends on Phase 4 because both extend transaction history display.
- **Phase 6 (US4)**: Depends on Phase 5 because it reuses transaction history template changes.
- **Phase 7 (US6)**: Depends on Phase 2; can run after US1 or in parallel with banking stories if staffed.
- **Phase 8 (US5)**: Depends on Phase 2; touches signup files also used by US1, so sequence after US1 for a single developer.
- **Phase 9 (Polish)**: Depends on the desired user stories being complete.

### User Story Dependencies

- **US1 (P1)**: Independent after foundational review.
- **US2 (P1)**: Independent after foundational review.
- **US3 (P2)**: Depends on US2 template/test groundwork.
- **US4 (P2)**: Depends on US3 transaction-history template groundwork.
- **US6 (P2)**: Independent of banking stories; shares `accounts/forms.py`, `accounts/views.py`, and `accounts/tests/test_views.py` with US5 and extends password criteria from US1.
- **US5 (P3)**: Independent of banking stories; sequence after US1 and US6 when one developer is editing accounts files.

### Within Each User Story

1. Write tests first and confirm they fail.
2. Implement forms/validators/services.
3. Implement views/routes.
4. Update templates.
5. Run focused tests before moving to the next story.

---

## Parallel Opportunities

### User Story 1

```text
T006 accounts/tests/test_validators.py
T007 accounts/tests/test_views.py
T011 accounts/templates/accounts/signup.html
T012 accounts/templates/accounts/password_reset_confirm.html
```

### User Story 4

```text
T021 banking/tests/test_services.py
T022 banking/tests/test_views.py
T023 banking/services.py
T024 banking/forms.py
```

### User Story 6

```text
T030 accounts/tests/test_forms.py
T031 accounts/tests/test_views.py
T032 accounts/tests/test_views.py
T034 banking/tests/test_views.py
```

### Polish

```text
T047 specs/002-ux-enhancements/quickstart.md
T048 pytest accounts/tests/ banking/tests/ -v
T049 pytest --cov=accounts --cov=banking --cov-report=term-missing
```

---

## Implementation Strategy

### MVP First

1. Complete Phase 1 and Phase 2.
2. Complete Phase 3 (US1 password criteria).
3. Complete Phase 4 (US2 transfer party visibility).
4. Stop and validate P1 stories before moving to P2 work.

### Incremental Delivery

1. US1: Password criteria guidance and backend enforcement.
2. US2: Transfer party visibility.
3. US3: Transaction IDs in history.
4. US4: Transfer descriptions.
5. US6: User details and credential update flow.
6. US5: Optional initial balance on registration.
7. Phase 9: Full regression, quality gates, and manual quickstart.

### Single Developer Order

US1 -> US2 -> US3 -> US4 -> US6 -> US5 -> Polish

### Two Developer Split

- Developer A: US1, US6, US5 in `accounts/`, `templates/base.html`, and `static/js/password-criteria.js`.
- Developer B: US2, US3, US4 in `banking/` templates, forms, views, services, and tests.

---

## Notes

- Every task uses the required `- [ ] T###` checklist format.
- User-story tasks include `[US#]` labels that match `specs/002-ux-enhancements/spec.md`.
- Tasks marked `[P]` avoid overlapping file edits where practical.
- Do not add model migrations unless T002 reveals an unexpected schema drift.
- Do not log raw usernames, email addresses, phone numbers, passwords, or balances during profile-update or credential-update audit logging.
