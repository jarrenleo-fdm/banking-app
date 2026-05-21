# Tasks: UX Enhancements

**Input**: Design documents from `specs/002-ux-enhancements/`
**Prerequisites**: plan.md ✅ spec.md ✅ research.md ✅ data-model.md ✅ contracts/services.md ✅ quickstart.md ✅

**Tests**: Included — Constitution Principle II (Test-First, NON-NEGOTIABLE) requires tests written before implementation.

**Organization**: Tasks grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on each other)
- **[Story]**: Which user story this task belongs to
- Tests MUST be written first and confirmed failing before the matching implementation tasks

---

## Phase 1: Setup

**Purpose**: Confirm no schema changes are needed before any implementation begins.

- [x] T001 Verify no database migrations are needed by running `python manage.py makemigrations --check` — expected: `No changes detected`

---

## Phase 2: User Story 1 — Password Criteria Guidance (Priority: P1) 🎯 MVP

**Goal**: Users see a real-time password criteria checklist on the registration and password reset forms, and the backend enforces the same rules.

**Independent Test**: Navigate to `/accounts/signup/`, type a password that is missing one criterion (e.g., no uppercase), submit — form must reject it. Criteria list must update visually as you type.

### Tests for User Story 1

> **Write these tests FIRST and confirm they FAIL before implementing**

- [x] T002 [P] [US1] Write unit tests for `PasswordComplexityValidator` (validate, get_help_text, each missing character class raises `ValidationError`) in `accounts/tests/test_validators.py` (new file)
- [x] T003 [P] [US1] Write view tests asserting signup POST rejects passwords missing each character class (uppercase, lowercase, digit, special char) in `accounts/tests/test_views.py`

### Implementation for User Story 1

- [x] T004 [US1] Create `accounts/validators.py` with `PasswordComplexityValidator` class — enforce at least one uppercase, one lowercase, one digit, one special character; implement `validate()` and `get_help_text()`
- [x] T005 [US1] Register `PasswordComplexityValidator` in `banking_app/settings.py` `AUTH_PASSWORD_VALIDATORS` list (depends on T004)
- [x] T006 [US1] Create `static/js/password-criteria.js` — real-time checklist logic: on `input` event for password fields, check each of the 5 criteria and toggle a CSS class on the corresponding list item
- [x] T007 [P] [US1] Add password criteria checklist HTML and `<script src>` reference to `accounts/templates/accounts/signup.html` (depends on T006)
- [x] T008 [P] [US1] Add the same password criteria checklist to `accounts/templates/accounts/password_reset_confirm.html` (depends on T006)

**Checkpoint**: Signup and password reset both reject weak passwords (backend) and show the criteria checklist (frontend). Test with `pytest accounts/` — all US1 tests pass.

---

## Phase 3: User Story 2 — Transfer Party Visibility in History (Priority: P1)

**Goal**: Each transfer entry in transaction history clearly labels whether the counterparty is the sender (incoming) or the recipient (outgoing), showing their name.

**Independent Test**: Perform a transfer between two test accounts; in each account's transaction history, the counterparty name appears with a clear "From:" or "To:" label.

### Tests for User Story 2

- [x] T009 [US2] Write view tests asserting that `TRANSFER_OUT` history rows show recipient name with a "To:" label and `TRANSFER_IN` rows show sender name with a "From:" label in `banking/tests/test_views.py`

### Implementation for User Story 2

- [x] T010 [US2] Update `banking/templates/banking/transactions.html` "Other Party" column to display "From: {name}" for `TRANSFER_IN` and "To: {name}" for `TRANSFER_OUT` using Django template conditionals (counterparty data already loaded via `select_related`)

**Checkpoint**: Transaction history shows directional counterparty labels. Run `pytest banking/tests/test_views.py` — US2 tests pass.

---

## Phase 4: User Story 3 — Transaction ID in History (Priority: P2)

**Goal**: Every entry in the transaction history shows a unique transaction ID, giving users a reference number for support or auditing.

**Independent Test**: Check transaction history — every row has a non-empty, unique transaction ID displayed.

### Tests for User Story 3

- [x] T011 [US3] Add view tests asserting every transaction history row displays `transaction.pk` and that two different transactions show different IDs in `banking/tests/test_views.py`

### Implementation for User Story 3

- [x] T012 [US3] Add a "Transaction ID" column to `banking/templates/banking/transactions.html` displaying `{{ transaction.pk }}` for every row (same file as T010 — apply sequentially)

**Checkpoint**: All history rows show a transaction ID. Run `pytest banking/tests/test_views.py` — US2 and US3 tests pass.

---

## Phase 5: User Story 4 — Transfer Description (Priority: P2)

**Goal**: Users can attach an optional description to a transfer; it is stored on both the sender's and recipient's transaction records and shown in their respective histories.

**Independent Test**: Send a transfer with description "Rent May" — verify that description appears for the TRANSFER_OUT row in sender's history and the TRANSFER_IN row in recipient's history. Send one without a description — no description label shown.

### Tests for User Story 4

- [x] T013 [P] [US4] Add service tests asserting `transfer()` with a description stores the description on both the `TRANSFER_OUT` and `TRANSFER_IN` Transaction records in `banking/tests/test_services.py`
- [x] T014 [P] [US4] Add view tests asserting the transfer form accepts a description field and that the submitted description appears in the history template for both accounts in `banking/tests/test_views.py`

### Implementation for User Story 4

- [x] T015 [P] [US4] Update `banking/services.py` — add `description: str = ""` parameter to `transfer()`; pass it to both `Transaction.objects.create()` calls
- [x] T016 [P] [US4] Add optional `description` `CharField(max_length=200, required=False)` to `TransferForm` in `banking/forms.py`
- [x] T017 [US4] Update `banking/views.py` `transfer_view` to extract `form.cleaned_data["description"]` and pass it to `transfer()` (depends on T015, T016)
- [x] T018 [US4] Add description label and input to the Transfer card in `banking/templates/banking/dashboard.html` (depends on T016)
- [x] T019 [US4] Show description in `banking/templates/banking/transactions.html` — render a description row beneath each transfer entry only when `transaction.description` is non-empty (depends on T015; same file as T010/T012 — apply sequentially)

**Checkpoint**: Transfer description flows through form → service → both transaction records → both history views. Run `pytest banking/` — all US4 tests pass.

---

## Phase 6: User Story 5 — Optional Initial Balance on Registration (Priority: P3)

**Goal**: Registration form accepts an optional initial balance (defaults to 0 if blank); the account is created with that opening balance.

**Independent Test**: Register with initial balance 500.00 — dashboard shows $500.00. Register with field blank — dashboard shows $0.00. Submit −100 — form rejects with validation error.

### Tests for User Story 5

- [x] T020 [US5] Add view tests for: (a) signup with initial_balance=500 creates account with balance 500, (b) blank initial_balance creates account with balance 0, (c) negative initial_balance is rejected with a form error in `accounts/tests/test_views.py`

### Implementation for User Story 5

- [x] T021 [US5] Add optional `initial_balance` `DecimalField(min_value=0, required=False, initial=0)` with a `clean_initial_balance` method to `RegistrationForm` in `accounts/forms.py`
- [x] T022 [US5] Update `signup_view` in `accounts/views.py` — after `form.save()`, if `initial_balance > 0`, fetch `user.account` and call `account.save(update_fields=["balance"])` with the cleaned value (depends on T021)

**Checkpoint**: All five user stories fully functional. Run `pytest` — full suite passes.

---

## Phase 7: Polish & Cross-Cutting Concerns

- [x] T023 [P] Run full test suite with coverage: `pytest --cov=accounts --cov=banking --cov-report=term-missing` — all tests pass, no coverage regression
- [x] T024 [P] Run all pre-commit hooks: `pre-commit run --all-files` — flake8 and pylint pass; bandit incompatible with Python 3.14 (pre-existing infrastructure issue, not introduced by this feature)
- [ ] T025 Manual end-to-end verification of all five user stories per `specs/002-ux-enhancements/quickstart.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies — start immediately
- **Phase 2 (US1)**: Depends on Phase 1 — no other story depends on US1
- **Phase 3 (US2)**: Depends on Phase 1 — independent of US1; can start in parallel with Phase 2 if staffed
- **Phase 4 (US3)**: Depends on Phase 3 completion (same template file — apply sequentially)
- **Phase 5 (US4)**: Depends on Phase 4 completion (same template file — apply sequentially)
- **Phase 6 (US5)**: Depends on Phase 1 — independent of all other stories; can start in parallel with Phases 2–5 if staffed
- **Phase 7 (Polish)**: Depends on all story phases completing

### User Story Dependencies

- **US1 (P1)**: Independent — start after Phase 1
- **US2 (P1)**: Independent — start after Phase 1; can run in parallel with US1
- **US3 (P2)**: Depends on US2 completion (both modify `transactions.html` and `test_views.py`)
- **US4 (P2)**: Depends on US3 completion (`transactions.html` chain)
- **US5 (P3)**: Independent of US1–US4 — touches only `accounts/` files

### Within Each User Story

1. Write tests first — confirm they **FAIL** before implementation
2. Create/modify logic files
3. Update templates last
4. Run `pytest` for that app — confirm all story tests pass before moving on

### Files Modified Per Story (conflict map)

| File | US1 | US2 | US3 | US4 | US5 |
|---|---|---|---|---|---|
| `accounts/validators.py` | T004 | | | | |
| `banking_app/settings.py` | T005 | | | | |
| `static/js/password-criteria.js` | T006 | | | | |
| `accounts/templates/.../signup.html` | T007 | | | | |
| `accounts/templates/.../password_reset_confirm.html` | T008 | | | | |
| `banking/templates/banking/transactions.html` | | T010 | T012 | T019 | |
| `banking/forms.py` | | | | T016 | |
| `banking/services.py` | | | | T015 | |
| `banking/views.py` | | | | T017 | |
| `banking/templates/banking/dashboard.html` | | | | T018 | |
| `accounts/forms.py` | | | | | T021 |
| `accounts/views.py` | | | | | T022 |

---

## Parallel Opportunities

### Within Phase 2 (US1)

```
# Tests (run in parallel — different files):
T002 accounts/tests/test_validators.py
T003 accounts/tests/test_views.py

# Templates (run in parallel after T006 — different files):
T007 signup.html
T008 password_reset_confirm.html
```

### Within Phase 5 (US4)

```
# Tests (run in parallel — different files):
T013 banking/tests/test_services.py
T014 banking/tests/test_views.py

# Core logic (run in parallel — different files):
T015 banking/services.py
T016 banking/forms.py
```

### Phase 7 Polish

```
# Static analysis (run in parallel — independent tools):
T023 pytest
T024 pre-commit
```

---

## Implementation Strategy

### MVP (User Story 1 only)

1. Complete Phase 1 (T001)
2. Complete Phase 2 (T002–T008)
3. Validate: password criteria checklist works on signup and reset
4. Stop and demo if needed

### Incremental Delivery

1. Phase 1 → T001
2. Phase 2 → US1 complete: password security hardened
3. Phase 3 → US2 complete: transfer party visible in history
4. Phase 4 → US3 complete: transaction IDs visible
5. Phase 5 → US4 complete: transfer descriptions end-to-end
6. Phase 6 → US5 complete: initial balance on registration
7. Phase 7 → Polish: full test suite + static analysis + manual sign-off

### Parallel Team Strategy

Single developer (recommended order): US1 → US2 → US3 → US4 → US5

Two developers:
- Dev A: US1 (accounts app, JS)
- Dev B: US2 → US3 → US4 (banking app templates and services)
- Both merge, then Dev A or B handles US5 (accounts/forms + views only)

---

## Notes

- `[P]` = different files, no mutual dependency — safe to run in parallel
- `[Story]` maps each task to the user story it delivers
- `transactions.html` is modified in three sequential phases (T010 → T012 → T019) — never work on it in parallel
- `banking/tests/test_views.py` is extended in three sequential phases (T009 → T011 → T014) — append to the file sequentially
- Tests MUST fail before the matching implementation tasks are started (Constitution Principle II)
- Run `pre-commit run --all-files` after completing each phase
