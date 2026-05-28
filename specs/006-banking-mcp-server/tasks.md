# Tasks: Personal Banking MCP Server

**Input**: Design documents from `/specs/006-banking-mcp-server/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: Required. The implementation plan keeps the project under a test-first gate, so each story includes failing test tasks before implementation.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing. The overhauled `spec.md` is authoritative where older 006 design artifacts still mention business tools or username/password MCP login.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: Which user story this task belongs to (US1-US5)
- Include exact file paths in every task description

---

## Phase 1: Setup (Shared Documentation and Dependencies)

**Purpose**: Align the remaining 006 design artifacts with the overhauled personal-account-only, API-key-only spec before implementation starts.

- [X] T001 Update `specs/006-banking-mcp-server/plan.md` so the summary, tool count, project structure, implementation guide, and test plan describe only the 10 supported personal MCP tools and API-key-only login.
- [X] T002 [P] Update `specs/006-banking-mcp-server/data-model.md` to remove business-account entities and describe `accounts.CustomUser`, `accounts.AccountAPIKey`, `banking.Account`, `banking.Transaction`, `banking.Biller`, and API-key-backed session records.
- [X] T003 [P] Update `specs/006-banking-mcp-server/contracts/tool-schemas.md` to remove business tools and username/password login, make all existing-account reads protected by `session_token`, and define the 10 personal tool contracts from `specs/006-banking-mcp-server/spec.md`.
- [X] T004 [P] Update `specs/006-banking-mcp-server/quickstart.md` to show API-key login sequences, protected account reads, personal signup, personal transfers by phone number, biller management, and no business-account examples.
- [X] T005 Verify `mcp[cli]>=1.9,<2` remains declared in `requirements.txt` and update `requirements.txt` only if the dependency is missing.

**Checkpoint**: 006 docs no longer instruct implementers to expose business MCP tools, public account reads, or username/password MCP login.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Establish shared fixtures, token validation, and tool-surface cleanup that every user story depends on.

**CRITICAL**: No user story implementation should begin until this phase is complete.

- [X] T006 Add API-key test fixtures and helpers for authenticated MCP sessions, revoked keys, a second user, and seeded balances in `mcp_server/tests/conftest.py`.
- [X] T007 Update TokenStore tests in `mcp_server/tests/test_auth.py` to cover API-key-backed token issue, expiry, missing token rejection, revoked backing key rejection, and removal of password-auth token expectations.
- [X] T008 Implement API-key-only session token records in `mcp_server/auth.py`, requiring an API key identifier for issued MCP sessions and rejecting revoked backing keys on every protected validation.
- [X] T009 Replace obsolete business-tool behavior tests in `mcp_server/tests/test_business.py` with absence tests proving `get_business_account`, `list_business_transactions`, `list_pending_transactions`, `approve_transaction`, `reject_transaction`, and `create_business_account` are not registered MCP tools.
- [X] T010 Remove business model imports, business helper functions, business tool registrations, and username/password login registration from `mcp_server/server.py`.
- [X] T011 Add shared server helpers in `mcp_server/server.py` for validating `session_token`, resolving the authenticated user's personal `Account`, and returning structured session or authorisation errors.
- [X] T012 Run foundational checks for `mcp_server/tests/test_auth.py` and `mcp_server/tests/test_business.py`, keeping failing story-specific tests for later phases.

**Checkpoint**: The MCP package has an API-key-only personal-account foundation and no registered business tools.

---

## Phase 3: User Story 1 - Authenticate MCP Client With API Key (Priority: P1) MVP

**Goal**: MCP clients can create sessions only through valid active API keys; username/password MCP login is unavailable.

**Independent Test**: Use a valid active API key to receive a session token, then confirm invalid, malformed, revoked, expired, and password-login attempts do not create usable MCP sessions.

### Tests for User Story 1

> Write these tests first and confirm they fail before implementation.

- [X] T013 [P] [US1] Update `mcp_server/tests/test_api_key_auth.py` with failing tests for valid `login_with_api_key`, invalid key rejection, malformed key rejection, revoked key rejection, and safe generic authentication errors.
- [X] T014 [P] [US1] Update `mcp_server/tests/test_api_key_auth.py` with failing tests that a session created from a revoked API key is rejected by a protected tool before returning private data or changing balances.
- [X] T015 [P] [US1] Update `mcp_server/tests/test_api_key_auth.py` with failing tests that `login` is not importable or registered from `mcp_server/server.py` and that username/password credentials cannot create an MCP session.

### Implementation for User Story 1

- [X] T016 [US1] Implement `login_with_api_key(api_key: str)` as the only MCP login tool in `mcp_server/server.py`, returning `session_token`, `expires_in_minutes`, `username`, `auth_method`, and safe key identifier metadata on success.
- [X] T017 [US1] Ensure `mcp_server/server.py` catches API key authentication failures from `accounts/api_keys.py` and returns only `{"error": "Authentication failed."}`.
- [X] T018 [US1] Ensure `mcp_server/auth.py` purges expired tokens and rejects API-key-backed sessions whose `accounts.AccountAPIKey` record is revoked before protected tool execution.
- [X] T019 [US1] Run `pytest mcp_server/tests/test_api_key_auth.py mcp_server/tests/test_auth.py -v` and make US1 tests pass.

**Checkpoint**: User Story 1 is fully functional and independently testable.

---

## Phase 4: User Story 2 - Query Own Personal Account Information (Priority: P1)

**Goal**: An API-key-authenticated session can read only the owning user's personal account summary, transactions, and billers.

**Independent Test**: Authenticate as User A, retrieve User A's account summary, transactions, and billers, then confirm no valid path returns User B's private account data.

### Tests for User Story 2

> Write these tests first and confirm they fail before implementation.

- [X] T020 [P] [US2] Rewrite `mcp_server/tests/test_accounts.py` for protected `get_account(session_token)` success, missing-token rejection, revoked-token rejection, inclusion of phone number, and no username-targeting parameter.
- [X] T021 [P] [US2] Rewrite `mcp_server/tests/test_transactions.py` for protected `list_transactions(session_token, transaction_type=None, date_from=None, date_to=None, limit=20)` success, filters, newest-first ordering, empty history, limit cap, and missing-token rejection.
- [X] T022 [P] [US2] Update `mcp_server/tests/test_bills.py` list-biller tests for protected `list_billers(session_token)` success, empty list, missing-token rejection, revoked-token rejection, and no access to another user's billers.

### Implementation for User Story 2

- [X] T023 [US2] Implement protected `get_account(session_token: str)` in `mcp_server/server.py`, returning the authenticated user's username, name, phone number, balance, and account creation date.
- [X] T024 [US2] Implement protected `list_transactions(session_token: str, transaction_type: str = None, date_from: str = None, date_to: str = None, limit: int = 20)` in `mcp_server/server.py`, scoped to the authenticated user's account.
- [X] T025 [US2] Ensure transaction serialization in `mcp_server/server.py` includes transaction ID, type, amount, balance_after, timestamp, description, and counterparty identity where present.
- [X] T026 [US2] Implement protected `list_billers(session_token: str)` in `mcp_server/server.py`, scoped to the authenticated user's account and returning category, display name, reference, and creation date.
- [X] T027 [US2] Remove obsolete business-read imports and assertions from `mcp_server/tests/test_accounts.py` and `mcp_server/tests/test_transactions.py`.
- [X] T028 [US2] Run `pytest mcp_server/tests/test_accounts.py mcp_server/tests/test_transactions.py mcp_server/tests/test_bills.py::TestListBillers -v` and make US2 tests pass.

**Checkpoint**: User Story 2 is fully functional and independently testable.

---

## Phase 5: User Story 3 - Move Personal Funds (Priority: P2)

**Goal**: An API-key-authenticated session can deposit, withdraw, and transfer from only the owning user's personal account without overdrafts.

**Independent Test**: Authenticate as a user, perform valid deposit, withdrawal, and transfer operations, verify immutable transaction records and balances, then confirm invalid amounts, insufficient funds, missing sessions, revoked sessions, missing recipients, and self-transfers leave balances unchanged.

### Tests for User Story 3

> Write these tests first and confirm they fail before implementation.

- [X] T029 [P] [US3] Rewrite deposit tests in `mcp_server/tests/test_transfers.py` for `deposit_funds(amount, session_token)` success, missing-token rejection, revoked-token rejection, invalid amount rejection, and balance unchanged on failure.
- [X] T030 [P] [US3] Rewrite withdrawal tests in `mcp_server/tests/test_transfers.py` for `withdraw_funds(amount, session_token)` success, insufficient funds rejection, invalid amount rejection, missing-token rejection, revoked-token rejection, and balance unchanged on failure.
- [X] T031 [P] [US3] Rewrite transfer tests in `mcp_server/tests/test_transfers.py` for `transfer_funds(recipient_phone, amount, session_token, description="")` success, recipient phone lookup, description stored on both transactions, missing recipient rejection, self-transfer rejection, insufficient funds rejection, invalid amount rejection, and balance unchanged on failure.

### Implementation for User Story 3

- [X] T032 [US3] Implement `deposit_funds(amount: str, session_token: str)` in `mcp_server/server.py`, validating amount before depositing into the authenticated user's account.
- [X] T033 [US3] Implement `withdraw_funds(amount: str, session_token: str)` in `mcp_server/server.py`, validating amount and rejecting overdrafts before changing the authenticated user's account.
- [X] T034 [US3] Implement `transfer_funds(recipient_phone: str, amount: str, session_token: str, description: str = "")` in `mcp_server/server.py`, delegating to personal transfer services and using phone-number recipient lookup.
- [X] T035 [US3] Enforce transfer description length and structured validation errors for MCP money movement in `mcp_server/server.py` and `mcp_server/utils.py`.
- [X] T036 [US3] Run `pytest mcp_server/tests/test_transfers.py -v` and make US3 tests pass.

**Checkpoint**: User Story 3 is fully functional and independently testable.

---

## Phase 6: User Story 4 - Manage and Pay Personal Billers (Priority: P2)

**Goal**: An API-key-authenticated session can add fixed-category billers, list them, and pay only the authenticated user's own billers.

**Independent Test**: Authenticate as a user, add a biller with a valid category and reference, list it, pay it with sufficient funds, then confirm duplicate billers, unsupported categories, blank references, insufficient funds, wrong-owner billers, missing sessions, and revoked sessions are rejected.

### Tests for User Story 4

> Write these tests first and confirm they fail before implementation.

- [X] T037 [P] [US4] Add `TestAddBiller` coverage to `mcp_server/tests/test_bills.py` for `add_biller(session_token, category, reference)` success, invalid category, blank reference, duplicate category and reference, missing-token rejection, revoked-token rejection, and no cross-account writes.
- [X] T038 [P] [US4] Rewrite pay-bill tests in `mcp_server/tests/test_bills.py` for `pay_bill(biller_id, amount, session_token)` success, wrong-owner biller rejection, missing biller rejection, insufficient funds, invalid amount, missing-token rejection, revoked-token rejection, and balance unchanged on failure.

### Implementation for User Story 4

- [X] T039 [US4] Implement `add_biller(session_token: str, category: str, reference: str)` in `mcp_server/server.py`, validating `banking.models.Biller` category choices and mandatory reference before saving to the authenticated user's account.
- [X] T040 [US4] Catch duplicate biller constraints in `mcp_server/server.py` and return `{"error": "A biller with this category and reference already exists."}` without creating another `banking.models.Biller`.
- [X] T041 [US4] Implement `pay_bill(biller_id: int, amount: str, session_token: str)` in `mcp_server/server.py`, scoped to the authenticated user's account and delegating to the existing bill payment service.
- [X] T042 [US4] Run `pytest mcp_server/tests/test_bills.py -v` and make US4 tests pass.

**Checkpoint**: User Story 4 is fully functional and independently testable.

---

## Phase 7: User Story 5 - Open a Personal Account Through MCP (Priority: P3)

**Goal**: An unauthenticated caller can create a personal account through MCP, while authenticated MCP access still requires a separately generated API key.

**Independent Test**: Create a personal account with unique identity fields and optional initial balance, then confirm duplicate username, email, phone number, invalid phone number, weak password, negative amount, non-numeric amount, and over-precise amount are rejected without partial account creation.

### Tests for User Story 5

> Write these tests first and confirm they fail before implementation.

- [X] T043 [P] [US5] Create `mcp_server/tests/test_creation.py` with failing tests for successful `create_personal_account` with positive `initial_deposit`, explicit zero initial balance, omitted initial balance, and no API key returned.
- [X] T044 [P] [US5] Add failing duplicate-field tests to `mcp_server/tests/test_creation.py` for duplicate username, duplicate email, and duplicate phone number.
- [X] T045 [P] [US5] Add failing validation tests to `mcp_server/tests/test_creation.py` for invalid phone number, weak password, negative initial balance, non-numeric initial balance, and over-precise initial balance.

### Implementation for User Story 5

- [X] T046 [US5] Implement `create_personal_account(name: str, username: str, email: str, phone_number: str, password: str, initial_deposit: str = "0.00")` in `mcp_server/server.py` using the existing custom user model and account creation signal.
- [X] T047 [US5] Validate personal signup uniqueness, phone number format, and password strength in `mcp_server/server.py` by reusing existing account validators or forms from `accounts/forms.py` and `accounts/validators.py`.
- [X] T048 [US5] Apply optional initial balance atomically in `mcp_server/server.py`, skipping deposit service calls for omitted or zero initial balance and rejecting invalid amounts before user creation.
- [X] T049 [US5] Run `pytest mcp_server/tests/test_creation.py -v` and make US5 tests pass.

**Checkpoint**: User Story 5 is fully functional and independently testable.

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Verify the full personal MCP surface, remove stale references, and run project quality gates.

- [X] T050 Run `pytest mcp_server/tests/ -v` and resolve failures in `mcp_server/` and `mcp_server/tests/`.
- [X] T051 Run `pytest mcp_server/tests/ --cov=mcp_server --cov-report=term-missing` and keep MCP coverage at or above 80% for `mcp_server/`.
- [X] T052 [P] Run `flake8 mcp_server/` and fix E/W violations in `mcp_server/`.
- [X] T053 [P] Run `pylint mcp_server/ --disable=C` and address non-cosmetic warnings in `mcp_server/`.
- [ ] T054 [P] Run `bandit -r mcp_server/` and address MEDIUM or HIGH findings in `mcp_server/`. Blocked locally: Bandit raises internal AST errors under Python 3.14 and skips MCP files.
- [X] T055 Run `python manage.py check` and fix Django configuration issues in `banking_app/settings.py`, `accounts/`, `banking/`, or `mcp_server/` only if they are caused by this feature.
- [X] T056 Validate the updated run instructions in `specs/006-banking-mcp-server/quickstart.md` by starting `python -m mcp_server` and confirming the process starts cleanly on stdio.
- [X] T057 Search `mcp_server/`, `mcp_server/tests/`, and `specs/006-banking-mcp-server/` for stale references to removed business MCP tools or username/password MCP login and remove any remaining feature-owned references.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies; can start immediately.
- **Foundational (Phase 2)**: Depends on Setup completion; blocks all user story implementation.
- **US1 (Phase 3)**: Depends on Foundational; provides the authentication boundary for US2-US4.
- **US2 (Phase 4)**: Depends on Foundational and US1; account reads require API-key sessions.
- **US3 (Phase 5)**: Depends on Foundational and US1; money movement requires API-key sessions.
- **US4 (Phase 6)**: Depends on Foundational and US1; biller writes require API-key sessions.
- **US5 (Phase 7)**: Depends on Foundational only; personal signup is open and can be implemented independently of protected tools.
- **Polish (Phase 8)**: Depends on all desired user stories being complete.

### User Story Dependencies

- **User Story 1 (P1)**: Must be completed before protected read/write stories can pass.
- **User Story 2 (P1)**: Requires US1 session validation but is otherwise independent of US3-US5.
- **User Story 3 (P2)**: Requires US1 session validation and existing personal banking services.
- **User Story 4 (P2)**: Requires US1 session validation and existing billing services.
- **User Story 5 (P3)**: Can be implemented after Foundational without US1, because signup is unauthenticated.

### Within Each User Story

- Tests must be written and confirmed failing before implementation.
- Shared helpers before tool implementation.
- Tool implementation before story checkpoint test command.
- Story checkpoint must pass before moving to another story unless working in parallel.

---

## Parallel Opportunities

- T002, T003, and T004 can run in parallel after T001 is understood.
- T013, T014, and T015 can run in parallel for US1 tests.
- T020, T021, and T022 can run in parallel for US2 tests.
- T029, T030, and T031 can run in parallel for US3 tests.
- T037 and T038 can run in parallel for US4 tests.
- T043, T044, and T045 can run in parallel for US5 tests.
- T052, T053, and T054 can run in parallel during polish after the test suite is green.

---

## Parallel Example: User Story 2

```bash
# Independent test-writing tasks for protected reads:
Task: "Rewrite protected account summary tests in mcp_server/tests/test_accounts.py"
Task: "Rewrite protected transaction listing tests in mcp_server/tests/test_transactions.py"
Task: "Update protected list-biller tests in mcp_server/tests/test_bills.py"
```

---

## Parallel Example: User Story 3

```bash
# Independent test-writing tasks for personal money movement:
Task: "Rewrite deposit tests in mcp_server/tests/test_transfers.py"
Task: "Rewrite withdrawal tests in mcp_server/tests/test_transfers.py"
Task: "Rewrite transfer tests in mcp_server/tests/test_transfers.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1 to align design artifacts.
2. Complete Phase 2 to remove obsolete tool surface and establish shared API-key session helpers.
3. Complete Phase 3 so MCP clients can authenticate only with API keys.
4. Stop and validate US1 with `pytest mcp_server/tests/test_api_key_auth.py mcp_server/tests/test_auth.py -v`.

### Incremental Delivery

1. Add US1 API-key-only authentication.
2. Add US2 protected account reads.
3. Add US3 personal money movement.
4. Add US4 personal biller management and bill payment.
5. Add US5 open personal signup.
6. Run Phase 8 polish and quality gates.

### Notes

- The old business account MCP implementation and tests are deliberately removed or converted into absence tests.
- Protected personal tools should derive the target account from the API-key session instead of accepting a target username.
- `create_personal_account` is the only open tool in this feature and must not create or return API keys.
- Existing web API-key management from `specs/007-mcp-api-key-auth/` remains the source for generating and revoking API keys.
