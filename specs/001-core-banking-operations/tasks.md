# Tasks: Core Banking Operations

**Input**: Design documents from `/specs/001-core-banking-operations/`
**Prerequisites**: plan.md ✅ | spec.md ✅ | research.md ✅ | data-model.md ✅ | contracts/ ✅

**Tests**: Mandatory for all money-handling paths (Constitution Principle II — NON-NEGOTIABLE).
Test tasks are marked with `> Write test FIRST. Confirm it FAILS before implementing.`

**Organization**: Tasks are grouped by user story to enable independent implementation and
testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no blocking dependencies on incomplete tasks)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- Every task includes an exact file path

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project scaffolding — establishes directory layout and tooling before any feature work

- [X] T001 Initialize Django project (`django-admin startproject banking_app .`) and create `accounts` and `banking` apps (`manage.py startapp`) per project structure in plan.md
- [X] T002 Configure `banking_app/settings.py`: `INSTALLED_APPS` (accounts, banking, django.contrib.messages), `django-environ` `.env` parsing for `SECRET_KEY`/`DEBUG`/`ALLOWED_HOSTS`, `PASSWORD_HASHERS` with Argon2 first, `LOGIN_URL`/`LOGIN_REDIRECT_URL`, `PASSWORD_RESET_TIMEOUT = 3600`, security middleware defaults (`X_FRAME_OPTIONS`, `SECURE_CONTENT_TYPE_NOSNIFF`)
- [X] T003 [P] Create `requirements.txt` (pinned): `Django~=5.2`, `django[argon2]`, `django-environ`, `gunicorn`; create `requirements-dev.txt` (pinned): `pytest-django`, `factory-boy`, `flake8`, `pylint`, `bandit`, `pre-commit`, `pytest-cov`
- [X] T004 [P] Create `.env.example` with all required keys: `SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS`, `EMAIL_BACKEND`, `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`
- [X] T005 [P] Create `.pre-commit-config.yaml` with hooks for `flake8`, `bandit`, and `pylint` (compensating controls for Prototype tier per plan.md Complexity Tracking)
- [X] T006 Create skeleton `banking_app/urls.py` with `admin.site.urls` and `include()` placeholders for `accounts.urls` and `banking.urls`
- [X] T007 [P] Create `templates/base.html`: HTML5 boilerplate, nav bar with links (dashboard, transactions, logout if authenticated; login/signup if not), Django messages block, `{% block content %}` slot; create `static/` directory

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core models and infrastructure that MUST be complete before ANY user story begins

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T008 Create `accounts/managers.py` with `CustomUserManager` (overrides `create_user` and `create_superuser`; normalizes email to lowercase; sets Argon2-hashed password via `set_password`)
- [X] T009 Create `CustomUser` model in `accounts/models.py`: extends `AbstractBaseUser`; fields: `username` (CharField 150, case-insensitive unique via `UniqueConstraint(Lower('username'), name='unique_username_case_insensitive')`), `username_display` removed (store original casing in `username` field directly — use `iexact` for lookup), `email` (EmailField unique), `name` (CharField 150), `phone_number` (CharField 8, unique, `RegexValidator(r'^[89]\d{7}$')`), `is_active`, `is_staff`, `date_joined`; `USERNAME_FIELD = 'username'`; `REQUIRED_FIELDS = ['email', 'name', 'phone_number']`; `AUTH_USER_MODEL = 'accounts.CustomUser'` in settings
- [X] T010 [P] Create `Account` model in `banking/models.py`: `user` (OneToOneField → CustomUser, `on_delete=CASCADE`, `related_name='account'`), `balance` (DecimalField 12,2; default `Decimal('0.00')`), `created_at` (auto_now_add); add `post_save` signal on `CustomUser` to auto-create `Account`; add `TRANSACTION_TYPES` choices and `Transaction` model stub (fields only, no service logic): `account` (FK → Account, PROTECT), `transaction_type` (CharField 20, choices), `amount` (DecimalField 12,2), `balance_after` (DecimalField 12,2), `counterparty` (FK → Account, null=True, SET_NULL), `timestamp` (auto_now_add), `description` (CharField 200, blank)
- [X] T011 Create and apply initial migrations: `manage.py makemigrations accounts` then `manage.py makemigrations banking` then `manage.py migrate`; verify `db.sqlite3` created and schema is correct
- [X] T012 [P] Create `banking/services.py` with domain exception classes only: `BankingError(Exception)`, `InvalidAmountError(BankingError)`, `InsufficientFundsError(BankingError)`, `RecipientNotFoundError(BankingError)`, `SelfTransferError(BankingError)`; service functions are empty stubs (`raise NotImplementedError`) — implementations come in user story phases
- [X] T013 [P] Register `CustomUser` in `accounts/admin.py` (basic `ModelAdmin`); register `Account` and `Transaction` in `banking/admin.py` (`Transaction` with all `readonly_fields` to enforce immutability per FR-025); add `pytest.ini` or `pyproject.toml` with `[pytest]` section (`DJANGO_SETTINGS_MODULE`, `python_files`, `python_classes`, `python_functions`) and `conftest.py` at repo root

**Checkpoint**: `manage.py migrate` runs clean; `manage.py check` passes; `pytest` discovers test suite (zero tests, zero failures)

---

## Phase 3: User Story 1 — Open an Account and Manage Personal Funds (Priority: P1) 🎯 MVP

**Goal**: A visitor can register, log in, see their zero balance, deposit and withdraw money, and the system blocks overdrafts. Password reset via email works.

**Independent Test**: Register a new user → log in → confirm dashboard shows $0.00 → deposit $100 → confirm balance shows $100.00 → withdraw $30 → confirm balance shows $70.00 → attempt to withdraw $100 → confirm rejection and balance stays $70.00

### Tests for User Story 1 (Constitution Principle II — mandatory)

> Write these tests FIRST. Confirm they FAIL before implementing.

- [X] T014 [P] [US1] Write unit tests for `CustomUser` model in `accounts/tests/test_models.py`: case-insensitive username uniqueness, phone number validation (accepts `81234567`/`91234567`, rejects `12345678`/`8123456`/`+6581234567`), email stored lowercase, duplicate email/phone rejected
- [X] T015 [P] [US1] Write unit tests for `CustomUserManager` in `accounts/tests/test_models.py`: `create_user` hashes password with Argon2, `create_superuser` sets `is_staff=True`, creating user auto-creates `Account` with balance `0.00`
- [X] T016 [P] [US1] Write integration tests for deposit service in `banking/tests/test_services.py`: positive amount increases balance by exact amount, creates `DEPOSIT` Transaction with correct `balance_after`, amount=0 raises `InvalidAmountError`, amount<0 raises `InvalidAmountError`
- [X] T017 [P] [US1] Write integration tests for withdraw service in `banking/tests/test_services.py`: positive amount within balance decreases balance, creates `WITHDRAWAL` Transaction with correct `balance_after`, withdrawal > balance raises `InsufficientFundsError` and balance unchanged, amount=0 raises `InvalidAmountError`
- [X] T018 [P] [US1] Write integration tests for auth views in `accounts/tests/test_views.py`: GET signup renders form, POST signup with valid data creates user and redirects to login, POST signup with duplicate username/email/phone shows error, POST login with valid credentials redirects to dashboard, POST login with wrong credentials shows generic error (no hint which field), POST logout ends session, unauthenticated dashboard access redirects to login
- [X] T019 [P] [US1] Write integration tests for dashboard and banking views in `banking/tests/test_views.py`: authenticated GET dashboard shows balance, POST deposit changes balance and redirects, POST deposit with negative amount rejected, POST withdraw changes balance and redirects, POST withdraw exceeding balance rejected with unchanged balance

### Implementation for User Story 1

- [X] T020 [P] [US1] Create `RegistrationForm` in `accounts/forms.py`: `ModelForm` for `CustomUser`; `clean_phone_number()` strips spaces/hyphens then validates regex; `clean_username()` checks case-insensitive uniqueness; `clean_email()` lowercases and checks uniqueness; `password1`/`password2` fields with `validate_password()`
- [X] T021 [P] [US1] Create `LoginForm` in `accounts/forms.py`: `username` and `password` fields; `authenticate()` uses `username__iexact` lookup; `clean()` raises single generic `ValidationError("Invalid username or password.")` on any auth failure (FR-005, no hint which field)
- [X] T022 [US1] Implement deposit service function `deposit(account: Account, amount: Decimal) -> Transaction` in `banking/services.py`: `@transaction.atomic`; validate `amount > 0` (raise `InvalidAmountError`); update `account.balance += amount`; `account.save()`; create and return `Transaction(type=DEPOSIT, amount=amount, balance_after=account.balance)` — no `select_for_update()` (SQLite prototype; see plan.md)
- [X] T023 [US1] Implement withdraw service function `withdraw(account: Account, amount: Decimal) -> Transaction` in `banking/services.py`: `@transaction.atomic`; validate `amount > 0`; validate `account.balance >= amount` (raise `InsufficientFundsError`); update balance; create `WITHDRAWAL` Transaction
- [X] T024 [P] [US1] Implement registration view in `accounts/views.py`: GET renders `RegistrationForm`; POST validates form, calls `form.save()`, flashes success message, redirects to login
- [X] T025 [P] [US1] Implement login view in `accounts/views.py`: uses `LoginForm`; on success calls `auth_login()` and redirects to `settings.LOGIN_REDIRECT_URL`; on failure re-renders with generic error; implement logout view: calls `auth_logout()`, redirects to login
- [X] T026 [P] [US1] Wire Django's built-in password reset views in `accounts/views.py` / `accounts/urls.py`: `PasswordResetView` (custom `email_template_name`, `subject_template_name`), `PasswordResetDoneView`, `PasswordResetConfirmView` (invalidates other sessions via `update_session_auth_hash`), `PasswordResetCompleteView`; `PASSWORD_RESET_TIMEOUT = 3600` in settings
- [X] T027 [P] [US1] Create `DepositForm` and `WithdrawForm` in `banking/forms.py`: single `amount` field (`DecimalField`, `min_value=Decimal('0.01')`, `max_digits=12`, `decimal_places=2`)
- [X] T028 [US1] Implement dashboard view in `banking/views.py`: `@login_required`; GET fetches `request.user.account`; passes `account`, `balance`, last-5 transactions, `DepositForm`, `WithdrawForm` to template; POST to deposit/withdraw endpoints handled separately
- [X] T029 [US1] Implement deposit view and withdraw view in `banking/views.py`: both `@login_required` POST-only; call `services.deposit()` / `services.withdraw()` with validated form amount; catch `InvalidAmountError` / `InsufficientFundsError`, re-render dashboard with error message; on success flash message and redirect to dashboard
- [X] T030 [P] [US1] Create `accounts/urls.py`: paths for signup, login, logout, password-reset (4 built-in views); wire into `banking_app/urls.py` under prefix `accounts/`
- [X] T031 [P] [US1] Create `banking/urls.py`: paths for dashboard (`/`), deposit (`deposit/`), withdraw (`withdraw/`); wire into `banking_app/urls.py` at root
- [X] T032 [P] [US1] Create `accounts/templates/accounts/signup.html`: extends base, registration form with field errors, link to login
- [X] T033 [P] [US1] Create `accounts/templates/accounts/login.html`: extends base, login form with generic error display, links to signup and password reset
- [X] T034 [P] [US1] Create password reset templates: `accounts/password_reset.html` (email form), `accounts/password_reset_done.html` (confirmation message identical regardless of email match), `accounts/password_reset_confirm.html` (new password form + invalid-link state), `accounts/password_reset_complete.html` (success + login link)
- [X] T035 [US1] Create `banking/templates/banking/dashboard.html`: extends base; displays balance formatted to 2 d.p.; renders deposit and withdraw forms; shows 5 most-recent transactions (type, amount, timestamp, balance_after); flash message area

**Checkpoint**: User Story 1 independently testable. Register → Login → Dashboard → Deposit → Withdraw → Overdraft rejection → Logout all work. `pytest accounts/ banking/tests/test_services.py banking/tests/test_views.py -v` passes.

---

## Phase 4: User Story 2 — Send and Receive Money (Priority: P2)

**Goal**: A logged-in user can send a positive amount to another user identified by phone number; sender's balance decreases and recipient's increases atomically; overdraft and self-transfer are rejected.

**Independent Test**: Register two users (Alice `81111111`, Bob `82222222`); Alice deposits $200; Alice transfers $50 to `82222222`; confirm Alice balance = $150, Bob balance = $50; attempt Alice → Alice transfer → rejected; attempt transfer of $200 from Alice (balance $150) → rejected; both balances unchanged.

### Tests for User Story 2 (Constitution Principle II — mandatory)

> Write these tests FIRST. Confirm they FAIL before implementing.

- [X] T036 [P] [US2] Write integration tests for transfer service in `banking/tests/test_services.py`: valid transfer decreases sender and increases recipient by exact amount, creates two Transaction records atomically (TRANSFER_OUT + TRANSFER_IN with correct counterparty references), transfer exceeding sender balance raises `InsufficientFundsError` and neither balance changes, unknown recipient phone raises `RecipientNotFoundError`, sender == recipient raises `SelfTransferError`, amount ≤ 0 raises `InvalidAmountError`
- [X] T037 [P] [US2] Write integration tests for transfer view in `banking/tests/test_views.py`: valid POST creates transfer and redirects with success flash, insufficient funds shows error, unknown recipient shows error, self-transfer shows error, invalid amount shows error, unauthenticated POST redirects to login

### Implementation for User Story 2

- [X] T038 [P] [US2] Create `TransferForm` in `banking/forms.py`: `recipient_phone` (CharField, `RegexValidator(r'^[89]\d{7}$')`, cleaned via `strip()`+remove hyphens); `amount` (DecimalField, `min_value=Decimal('0.01')`, max_digits=12, decimal_places=2)
- [X] T039 [US2] Implement transfer service function `transfer(sender_account: Account, recipient_phone: str, amount: Decimal) -> tuple[Transaction, Transaction]` in `banking/services.py`: `@transaction.atomic`; validate amount > 0; look up recipient `Account` via `CustomUser.phone_number = recipient_phone` (raise `RecipientNotFoundError` if not found); reject self-transfer; validate `sender.balance >= amount`; debit sender, credit recipient, `save()` both; create TRANSFER_OUT and TRANSFER_IN Transaction records; return both records
- [X] T040 [US2] Implement transfer view in `banking/views.py`: `@login_required` POST-only; validates `TransferForm`; calls `services.transfer()`; catches all `BankingError` subclasses and re-renders dashboard with error; on success flash "Sent $X to [recipient name]" and redirect to dashboard
- [X] T041 [US2] Add transfer URL `transfer/` to `banking/urls.py`
- [X] T042 [US2] Update `banking/templates/banking/dashboard.html` to include `TransferForm` (pass `TransferForm` from dashboard view context); add transfer section below deposit/withdraw forms; display transfer errors inline

**Checkpoint**: User Story 2 independently testable. Two-account transfer, overdraft rejection, self-transfer rejection, unknown recipient rejection all work. `pytest banking/tests/test_services.py banking/tests/test_views.py -v` passes.

---

## Phase 5: User Story 3 — View Transaction History (Priority: P3)

**Goal**: A logged-in user can view their complete transaction history, most recent first, with each entry showing type, amount, timestamp, resulting balance, and counterparty (for transfers).

**Independent Test**: Perform deposit, withdrawal, and transfer with a test account; open `/banking/transactions/`; confirm all three transactions appear in reverse chronological order; confirm each shows correct type, amount, balance_after, and counterparty for the transfer; confirm a second user cannot see the first user's history.

### Tests for User Story 3 (Constitution Principle II — mandatory)

> Write these tests FIRST. Confirm they FAIL before implementing.

- [X] T043 [P] [US3] Write integration tests for transaction history view in `banking/tests/test_views.py`: authenticated GET returns all transactions for the user ordered by `-timestamp`, each has correct type/amount/balance_after, transfer transactions show counterparty, a user with no transactions sees empty-state message, user A cannot see user B's transactions (returns only user A's), unauthenticated GET redirects to login

### Implementation for User Story 3

- [X] T044 [US3] Implement transaction history view in `banking/views.py`: `@login_required`; fetches `request.user.account.transactions.select_related('counterparty__user').order_by('-timestamp')`; passes queryset and account to `banking/transactions.html`
- [X] T045 [US3] Add history URL `transactions/` to `banking/urls.py`
- [X] T046 [US3] Create `banking/templates/banking/transactions.html`: extends base; table of all transactions with columns: Date/Time, Type, Amount, Balance After, Other Party (counterparty name + phone for transfers, blank otherwise); empty-state message "You have no transactions yet." when queryset is empty
- [X] T047 [US3] Add "View full history" link on `banking/templates/banking/dashboard.html` pointing to `/banking/transactions/`

**Checkpoint**: All three user stories work end-to-end. `pytest --cov=accounts --cov=banking --cov-report=term-missing` passes with ≥ 80% coverage.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Security hardening, admin polish, and validation that the quickstart works

- [X] T048 [P] Harden `banking_app/settings.py`: confirm `SECURE_CONTENT_TYPE_NOSNIFF = True`, `X_FRAME_OPTIONS = 'DENY'`, `SESSION_COOKIE_HTTPONLY = True`, `CSRF_COOKIE_HTTPONLY = True`; add `MESSAGE_STORAGE = 'django.contrib.messages.storage.cookie.CookieStorage'`; confirm `DEBUG = False` path sets all production-safe flags; run `manage.py check --deploy` and resolve all warnings
- [X] T049 [P] Finalize `banking/admin.py`: `Transaction` registered with `list_display = ['account', 'transaction_type', 'amount', 'balance_after', 'timestamp', 'counterparty']` and all fields in `readonly_fields` (FR-025 — no update/delete); `Account` registered with `readonly_fields = ['balance', 'created_at']`
- [X] T050 [P] Run pre-commit hooks across entire codebase (`pre-commit run --all-files`); fix all flake8/bandit/pylint findings
- [X] T051 Follow `specs/001-core-banking-operations/quickstart.md` step-by-step on a clean virtual environment; confirm `manage.py migrate`, `manage.py runserver`, registration, login, deposit, withdraw, transfer, history, password reset all work as documented
- [X] T052 Add Production Migration TODO reminder comment in `banking_app/settings.py` referencing `specs/001-core-banking-operations/plan.md#production-migration-todo` so future contributors see the PostgreSQL migration requirements

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 — BLOCKS all user stories
- **US1 (Phase 3)**: Depends on Phase 2 — **MVP increment**
- **US2 (Phase 4)**: Depends on Phase 2 (models); integrates with Phase 3 dashboard
- **US3 (Phase 5)**: Depends on Phase 3 (transactions to display); read-only, no service changes
- **Polish (Phase 6)**: Depends on all story phases complete

### User Story Dependencies

- **US1 (P1)**: No dependency on US2 or US3 — independently buildable and testable after Phase 2
- **US2 (P2)**: Models come from Phase 2; dashboard integration touches Phase 3 templates — implement Phase 3 first
- **US3 (P3)**: Read-only history; depends on transactions existing (Phase 3 creates them) — can be built any time after Phase 3

### Within Each User Story

1. Write tests → confirm they FAIL
2. Implement models/forms (parallel where marked [P])
3. Implement services
4. Implement views (depend on services)
5. Wire URLs
6. Create templates
7. Confirm tests PASS

### Parallel Opportunities

- All Phase 1 tasks marked [P] can run simultaneously
- Phase 2: T010 (banking models) can run in parallel with T008/T009 (accounts models)
- Phase 3 tests (T014–T019) can all run in parallel
- Phase 3 forms (T020, T021, T027) can run in parallel
- Phase 3 templates (T032–T035) can run in parallel after views exist
- Phase 4 tests (T036, T037) can run in parallel

---

## Parallel Example: User Story 1

```bash
# All US1 tests can be written in parallel (different files):
Task T014: accounts/tests/test_models.py     — CustomUser model tests
Task T015: accounts/tests/test_models.py     — CustomUserManager tests
Task T016: banking/tests/test_services.py    — deposit service tests
Task T017: banking/tests/test_services.py    — withdraw service tests
Task T018: accounts/tests/test_views.py      — auth view tests
Task T019: banking/tests/test_views.py       — dashboard + banking view tests

# After tests written and failing, these forms can be implemented in parallel:
Task T020: accounts/forms.py  — RegistrationForm
Task T021: accounts/forms.py  — LoginForm
Task T027: banking/forms.py   — DepositForm, WithdrawForm

# Templates can be built in parallel (no code dependencies):
Task T032: accounts/templates/accounts/signup.html
Task T033: accounts/templates/accounts/login.html
Task T034: accounts/templates/accounts/password_reset*.html (4 files)
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational — **CRITICAL, blocks everything**
3. Complete Phase 3: User Story 1 (tests first, then implementation)
4. **STOP and VALIDATE**: `pytest accounts/ banking/ -v` → all pass; manual walkthrough of registration → login → deposit → withdraw → overdraft rejection
5. Demo/deploy if ready

### Incremental Delivery

1. Phases 1–2 → Foundation ready
2. Phase 3 (US1) → Register, login, deposit, withdraw, password reset → **MVP**
3. Phase 4 (US2) → Peer-to-peer transfers → Extended feature
4. Phase 5 (US3) → Full transaction history → Complete feature
5. Phase 6 → Polish → Production-ready prototype

---

## Notes

- **[P]** = different files, no incomplete task dependencies — safe to parallelize
- **[Story]** label maps each task to its user story for traceability
- Tests MUST be written before the code they test; verify they fail first
- Use `Decimal` for all monetary values — never `float`
- Wrap all balance mutations in `@transaction.atomic` (no `select_for_update()` on SQLite — see plan.md)
- `Transaction` records are never updated or deleted — admin `readonly_fields` enforces this
- Each user story checkpoint should be validated manually before moving to the next
