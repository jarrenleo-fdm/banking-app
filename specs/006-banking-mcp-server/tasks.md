# Tasks: Banking MCP Server

**Input**: Design documents from `specs/006-banking-mcp-server/`
**Prerequisites**: plan.md ✅, spec.md ✅, data-model.md ✅, contracts/tool-schemas.md ✅, research.md ✅, quickstart.md ✅

**Tests**: Required — Principle II (Test-First / Red-Green-Refactor) is NON-NEGOTIABLE per constitution. Write tests first, confirm they FAIL, then implement.

**Organization**: Tasks grouped by user story to enable independent implementation and testing.

**Status**: 13 of 16 tools implemented and tested. Remaining: `add_biller` (US5 extension), `create_personal_account` and `create_business_account` (US8 — from clarifications 2026-05-26, FR-022 to FR-026).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1–US8)
- Include exact file paths in every task description

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create the `mcp_server/` Python package skeleton and install the MCP dependency.

- [x] T001 Create mcp_server/ package: touch mcp_server/__init__.py, mcp_server/server.py, mcp_server/auth.py, mcp_server/utils.py, mcp_server/tests/__init__.py
- [x] T002 Add `mcp[cli]>=1.9,<2` to requirements.txt
- [x] T003 Create mcp_server/tests/conftest.py: add `django_db_setup` marker, and fixtures `db_user` (CustomUser + Account), `db_business` (BusinessAccount + AccountManagerProfile + Authoriser), `db_biller` (Biller linked to db_user's account)

**Checkpoint**: `pytest mcp_server/tests/ -v` collects 0 tests without import errors.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Auth infrastructure, amount validation helper, and the FastMCP server skeleton. Every user story phase depends on this being complete.

**⚠️ CRITICAL**: No user story work begins until this phase is complete.

- [x] T004 Write failing tests for TokenStore: issue_token returns a 64-char hex string; validate_token returns username on fresh token; validate_token raises SessionExpiredError when last_used > timeout; _purge_expired removes expired entries in mcp_server/tests/test_auth.py
- [x] T005 Implement TokenStore (issue_token, validate_token, _purge_expired) and SessionExpiredError in mcp_server/auth.py — makes T004 green
- [x] T006 [P] Write failing tests for _mcp_validate_amount: "50.00" → Decimal("50.00"); "0" → ValueError; "-1.00" → ValueError; "10.001" → ValueError; "abc" → ValueError in mcp_server/tests/test_auth.py
- [x] T007 [P] Implement _mcp_validate_amount(amount: str) -> Decimal in mcp_server/utils.py: parse with Decimal, reject <= 0 and != quantize("0.01") — makes T006 green
- [x] T008 [P] Create FastMCP("banking") instance and global token_store = TokenStore() in mcp_server/server.py (no @mcp.tool() registrations yet)
- [x] T009 Implement mcp_server/__init__.py: os.environ.setdefault DJANGO_SETTINGS_MODULE → "banking_app.settings", django.setup(), import mcp from mcp_server.server, define main() calling mcp.run() and if __name__ == "__main__" guard

**Checkpoint**: `python -c "import mcp_server"` completes without error; all T004 and T006 tests are green.

---

## Phase 3: User Story 7 — User Login and Session Management (Priority: P1) 🔐

**Goal**: Models can authenticate with username + password and receive a short-lived session token. Write tools reject missing, expired, or wrong-owner tokens.

**Independent Test**: `login("alice", correct_password)` → `{"session_token": ..., "expires_in_minutes": 15}`; `login("alice", wrong_password)` → `{"error": "Authentication failed."}` with no token.

### Tests for US7

> **Write these FIRST — confirm they FAIL before touching the login tool**

- [x] T010 [US7] Write failing tests for login tool: valid creds → session_token (64 hex chars) + expires_in_minutes=15; wrong password → {"error": "Authentication failed."}; unknown username → same generic error (no token) in mcp_server/tests/test_auth.py

### Implementation for US7

- [x] T011 [US7] Implement login tool in mcp_server/server.py: use django.contrib.auth.authenticate(username, password), on success call token_store.issue_token(username) and return {"session_token": token, "expires_in_minutes": MCP_SESSION_TIMEOUT_MINUTES}, on failure return {"error": "Authentication failed."} — makes T010 green

**Checkpoint**: Login tool fully functional; T010 all green; `python -m mcp_server` starts without error.

---

## Phase 4: User Story 1 — Query Account Information (Priority: P1) 🎯 MVP

**Goal**: Models can retrieve personal and business account details without a session token.

**Independent Test**: `get_account(username="alice")` returns balance, holder name, and created_at. `get_business_account(identifier="202312345A")` returns company_name, UEN, address, balance, manager, and authoriser. Unknown identifiers return clear error dicts.

### Tests for US1

> **Write these FIRST — confirm they FAIL before implementing get_account / get_business_account**

- [x] T012 [P] [US1] Write failing tests for get_account: valid username → {username, name, balance as string, created_at ISO8601}; non-existent username → {"error": "..."}; no session_token required (call without one succeeds) in mcp_server/tests/test_accounts.py
- [x] T013 [P] [US1] Write failing tests for get_business_account: valid UEN → full business dict; valid company_name (case-insensitive) → same; unknown identifier → error dict in mcp_server/tests/test_accounts.py

### Implementation for US1

- [x] T014 [P] [US1] Implement get_account tool in mcp_server/server.py: User.objects.get(username=...), return account fields with str(balance) and created_at.isoformat(); catch DoesNotExist and return error dict — makes T012 green
- [x] T015 [P] [US1] Implement get_business_account tool in mcp_server/server.py: try BusinessAccount by uen first, then company_name__iexact; return all fields including manager and authoriser sub-dicts; catch DoesNotExist — makes T013 green

**Checkpoint**: Account query tools return correct data for all acceptance scenarios; T012/T013 all green.

---

## Phase 5: User Story 2 — Browse Transaction History (Priority: P1)

**Goal**: Models can retrieve and filter paginated transaction history for personal and business accounts without a session token.

**Independent Test**: `list_transactions(username="alice")` returns the 20 newest transactions newest-first. `list_transactions(username="alice", transaction_type="BILL_PAYMENT")` returns only bill payments. An account with no transactions returns `{"transactions": [], "count": 0}`.

### Tests for US2

> **Write these FIRST — confirm they FAIL before implementing list_transactions / list_business_transactions**

- [x] T016 [P] [US2] Write failing tests for list_transactions: no filter → 20 newest ordered by timestamp desc; transaction_type filter applied correctly; date_from/date_to filter applied correctly; limit capped at 100; account with no transactions → count=0 in mcp_server/tests/test_transactions.py
- [x] T017 [P] [US2] Write failing tests for list_business_transactions: same filter permutations; response shape does NOT include counterparty_username field in mcp_server/tests/test_transactions.py

### Implementation for US2

- [x] T018 [P] [US2] Implement list_transactions tool in mcp_server/server.py: look up Account via User, filter Transaction queryset by account, optional transaction_type, date_from/date_to (timestamp__date gte/lte), apply limit (default 20, max 100), return list of dicts with amount/balance_after as strings and timestamp as isoformat — makes T016 green
- [x] T019 [P] [US2] Implement list_business_transactions tool in mcp_server/server.py: resolve BusinessAccount by UEN or company_name__iexact, filter BusinessTransaction with same optional params, exclude counterparty_username from response — makes T017 green

**Checkpoint**: Transaction listing with all filters works for both account types; T016/T017 all green.

---

## Phase 6: User Story 3 — Execute Personal Account Transfers (Priority: P2)

**Goal**: Models can transfer funds between personal accounts atomically using a valid session token.

**Independent Test**: `transfer_funds(from_username="alice", to_username="bob", amount="50.00", session_token=<valid>)` deducts 50.00 from alice and adds 50.00 to bob with both Transaction records created. Insufficient funds, expired token, and wrong-owner token are all rejected before any DB change.

### Tests for US3

> **Write these FIRST — confirm they FAIL before implementing transfer_funds**

- [x] T020 [US3] Write failing tests for transfer_funds: valid transfer → {"sender_new_balance": str, "out_transaction_id": int, "in_transaction_id": int}; insufficient funds → error, both balances unchanged; unknown recipient → error; expired session_token → session error; token owner != from_username → not-authorised error; amount="0" → validation error; amount="10.001" → validation error in mcp_server/tests/test_transfers.py

### Implementation for US3

- [x] T021 [US3] Implement transfer_funds tool in mcp_server/server.py: call _mcp_validate_amount, then token_store.validate_token, verify token owner == from_username, look up recipient User by to_username, extract phone_number, call banking.services.transfer(sender_account, recipient_phone, amount, description), return balances and transaction IDs as dict; catch SessionExpiredError, PermissionError, InsufficientFundsError, DoesNotExist — makes T020 green

**Checkpoint**: transfer_funds fully functional with auth and validation guards; T020 all green.

---

## Phase 7: User Story 4 — Deposit and Withdraw Funds (Priority: P2)

**Goal**: Models can deposit into or withdraw from a personal account; both operations require a valid session token whose owner matches the account.

**Independent Test**: `deposit_funds(username="alice", amount="200.00", session_token=<valid>)` increases alice's balance by 200.00 and creates a DEPOSIT transaction. `withdraw_funds` with insufficient funds is rejected and the balance is unchanged.

### Tests for US4

> **Write these FIRST — confirm they FAIL before implementing deposit_funds / withdraw_funds**

- [x] T022 [P] [US4] Write failing tests for deposit_funds: valid deposit → {"new_balance": str, "transaction_id": int}; zero amount → validation error; expired token → session error; non-existent account → error in mcp_server/tests/test_transfers.py
- [x] T023 [P] [US4] Write failing tests for withdraw_funds: valid withdrawal → {"new_balance": str, "transaction_id": int}; insufficient funds → error, balance unchanged; wrong-owner token → not-authorised error; expired token → session error; negative amount → validation error in mcp_server/tests/test_transfers.py

### Implementation for US4

- [x] T024 [P] [US4] Implement deposit_funds tool in mcp_server/server.py: _mcp_validate_amount, validate_token, verify owner == username, look up Account, call banking.services.deposit(account, amount), return {"new_balance": str(account.balance), "transaction_id": txn.id} — makes T022 green
- [x] T025 [P] [US4] Implement withdraw_funds tool in mcp_server/server.py: same auth + owner check, call banking.services.withdraw(account, amount), return {"new_balance": str, "transaction_id": int}; catch InsufficientFundsError — makes T023 green

**Checkpoint**: Deposit and withdrawal functional with overdraft guard and auth; T022/T023 all green.

---

## Phase 8: User Story 5 — Manage and Pay Bills (Priority: P2)

**Goal**: Models can list saved billers for a personal account, add new billers, and submit bill payments using a valid session token.

**Independent Test**: `list_billers(username="alice")` returns all billers (id, category, reference). `pay_bill(username="alice", biller_id=7, amount="100.00", session_token=<valid>)` reduces the balance and creates a BILL_PAYMENT transaction. `add_biller(username="alice", category="ELECTRICITY", reference="ACC-123", session_token=<valid>)` saves the biller and returns its details.

### Completed (list_billers + pay_bill)

- [x] T026 [P] [US5] Write failing tests for list_billers: returns all billers with id, category, category_display, reference, created_at as isoformat; account with no billers → {"billers": [], "count": 0}; no session_token required in mcp_server/tests/test_bills.py
- [x] T027 [P] [US5] Write failing tests for pay_bill: valid payment → {"new_balance": str, "transaction_id": int}; biller_id not found → {"error": "Biller not found."}; biller belongs to different account → same Biller not found error; insufficient funds → {"error": "Insufficient funds."}; expired token → session error; wrong-owner token → not-authorised error; invalid amount → validation error in mcp_server/tests/test_bills.py
- [x] T028 [P] [US5] Implement list_billers tool in mcp_server/server.py: look up Account via User, query account.biller_set.all(), return list with get_name_display() for category_display and created_at.isoformat() — makes T026 green
- [x] T029 [P] [US5] Implement pay_bill tool in mcp_server/server.py: _mcp_validate_amount, validate_token, verify owner == username, look up Biller by biller_id scoped to account (raise "Biller not found." if missing or wrong account), call banking.services.pay_bill(account, biller, amount), return {"new_balance": str, "transaction_id": int} — makes T027 green

### Remaining — add_biller (Red-Green-Refactor)

> **Write tests FIRST — confirm they FAIL before implementing add_biller**

- [ ] T030 [US5] Add class `TestAddBiller` to `mcp_server/tests/test_bills.py`; write failing tests: success → returns `{"id": int, "category": "ELECTRICITY", "category_display": "Electricity", "reference": str, "created_at": str}`; invalid category value → `{"error": "Invalid category. Must be one of: ELECTRICITY, WATER_UTILITIES, INTERNET_BROADBAND, TELECOMMUNICATIONS, TOWN_COUNCIL."}`; duplicate category + reference for same account → `{"error": "A biller with this category and reference already exists."}`; expired token → session error; wrong-owner token → not-authorised error
- [ ] T031 [US5] Run `pytest mcp_server/tests/test_bills.py::TestAddBiller` and confirm all tests fail (add_biller not yet implemented)
- [ ] T032 [US5] Implement `add_biller` tool in `mcp_server/server.py`: validate `session_token` → verify owner == `username` → look up `Account` → validate `category` against `Biller.BILLER_CATEGORIES` key list → create `Biller(account=acct, name=category, reference=reference)` and call `.save()` → catch `IntegrityError` for duplicate (account, name, reference) constraint → return `{"id": b.pk, "category": b.name, "category_display": b.get_name_display(), "reference": b.reference, "created_at": b.created_at.isoformat()}`
- [ ] T033 [US5] Run `pytest mcp_server/tests/test_bills.py` and confirm all tests pass; refactor if needed

**Checkpoint**: US5 complete — billers can be listed, added, and paid; all `test_bills.py` tests pass

---

## Phase 9: User Story 6 — Manage Business Account Pending Transactions (Priority: P3)

**Goal**: Models acting as authorisers can list, approve, or reject pending business transactions. Only the assigned authoriser's token is accepted.

**Independent Test**: `list_pending_transactions(identifier="Acme Pte Ltd")` returns PENDING transactions. `approve_transaction(pending_transaction_id=3, session_token=<authoriser>)` changes status to APPROVED and updates the business balance. A non-authoriser token returns `{"error": "Not authorised to perform this action."}`.

### Tests for US6

> **Write these FIRST — confirm they FAIL before implementing any of the three business pending tools**

- [x] T034 [US6] Write failing tests for list_pending_transactions: returns PENDING transactions with id, transaction_type, amount as string, counterparty_username, description, created_at; business with no pending → {"pending_transactions": [], "count": 0}; unknown identifier → error in mcp_server/tests/test_business.py
- [x] T035 [US6] Write failing tests for approve_transaction: PENDING → APPROVED, business balance updated, {"status": "APPROVED", "business_new_balance": str} returned; non-PENDING status → {"error": "Transaction is no longer pending."}; non-authoriser session token → {"error": "Not authorised to perform this action."}; expired token → session error in mcp_server/tests/test_business.py
- [x] T036 [US6] Write failing tests for reject_transaction: PENDING → REJECTED, balance unchanged, {"status": "REJECTED"} returned; optional reason stored; same non-PENDING and non-authoriser error cases in mcp_server/tests/test_business.py

### Implementation for US6

- [x] T037 [US6] Implement list_pending_transactions tool in mcp_server/server.py: resolve BusinessAccount by UEN or company_name__iexact, filter PendingTransaction by business_account and status=PENDING, return list with amounts as strings and created_at as isoformat — makes T034 green
- [x] T038 [US6] Implement approve_transaction tool in mcp_server/server.py: validate_token, look up PendingTransaction, get Authoriser for business_account, verify token owner == authoriser.user.username, verify status==PENDING, call banking.services.approve_business_pending(pending_txn), return {"status": "APPROVED", "business_new_balance": str} — makes T035 green
- [x] T039 [US6] Implement reject_transaction tool in mcp_server/server.py: same token + authoriser + status checks, call banking.services.reject_business_pending(pending_txn, reason=""), return {"status": "REJECTED"} — makes T036 green

**Checkpoint**: All three business pending tools functional; authoriser enforcement confirmed; T034/T035/T036 all green.

---

## Phase 10: US8 — Open Account Signup (FR-022 to FR-026; clarifications 2026-05-26)

**Goal**: Unauthenticated callers can create a personal or business bank account; no session token required.

**Independent Test**: `pytest mcp_server/tests/test_creation.py` passes in isolation.

> **Write tests FIRST — confirm they FAIL before implementing either tool**

### create_personal_account (Red-Green-Refactor)

- [ ] T040 [P] [US8] Create `mcp_server/tests/test_creation.py` with class `TestCreatePersonalAccount`; write failing tests: success with positive `initial_deposit` → balance matches deposit; success with `initial_deposit="0.00"` → balance is `"0.00"` and no deposit service call made; duplicate `username` → `{"error": "Username is already taken."}`; duplicate `email` → `{"error": "Email is already registered."}`; duplicate `phone_number` → `{"error": "Phone number is already registered."}`; negative `initial_deposit` → `{"error": "Amount must be greater than zero."}`
- [ ] T041 [P] [US8] Run `pytest mcp_server/tests/test_creation.py::TestCreatePersonalAccount` and confirm all tests fail
- [ ] T042 [P] [US8] Implement `create_personal_account` tool in `mcp_server/server.py`: accepts `name`, `username`, `email`, `phone_number`, `password`, optional `initial_deposit` (default `"0.00"`); guards: if `initial_deposit != "0.00"` call `_mcp_validate_amount`; wraps `CustomUser.objects.create_user(username=..., email=..., name=..., phone_number=..., password=...)` + optional `services.deposit(user.account, amount)` in `@transaction.atomic`; catches `IntegrityError` for duplicate fields; returns `{"username": str, "name": str, "balance": str, "created_at": str}`
- [ ] T043 [P] [US8] Run `pytest mcp_server/tests/test_creation.py::TestCreatePersonalAccount` and confirm all tests pass; refactor if needed

### create_business_account (Red-Green-Refactor)

- [ ] T044 [P] [US8] Add class `TestCreateBusinessAccount` to `mcp_server/tests/test_creation.py`; write failing tests: success → response has `company_name`, `uen`, `balance`, `manager_username`, `manager_password`, `manager_phone`, `authoriser_username`, `authoriser_password`, `authoriser_phone`; `initial_deposit` below 7000 → `{"error": "Initial deposit must be at least 7,000."}`; duplicate UEN → `{"error": "A business account with this UEN already exists."}`; returned manager credentials valid (login tool returns a token); returned authoriser credentials valid (login tool returns a token)
- [ ] T045 [P] [US8] Run `pytest mcp_server/tests/test_creation.py::TestCreateBusinessAccount` and confirm all tests fail
- [ ] T046 [P] [US8] Implement `create_business_account` tool in `mcp_server/server.py`: accepts `company_name`, `uen`, `street`, `city`, `postal_code`, optional `initial_deposit` (default `"7000.00"`); validates `Decimal(initial_deposit) >= 7000`; delegates to `services.create_business_account_mock(company_name, uen, street, city, postal_code, initial_deposit)`; fetches `BusinessAccount.objects.get(pk=result["business_account_id"])` to populate `company_name`, `uen`, `balance`; catches `IntegrityError` for duplicate UEN; returns all 9 response fields
- [ ] T047 [P] [US8] Run `pytest mcp_server/tests/test_creation.py` and confirm all tests pass; refactor if needed

**Checkpoint**: US8 complete — personal and business accounts creatable via MCP with no session token; all `test_creation.py` tests pass

---

## Phase 11: Polish & Cross-Cutting Concerns

**Purpose**: Code quality verification and end-to-end coverage validation.

- [ ] T048 Run `pytest mcp_server/tests/ -v` and confirm all tests pass (all 16 tools covered)
- [ ] T049 Run `pytest mcp_server/tests/ --cov=mcp_server --cov-report=term-missing` and verify line coverage ≥ 80%
- [ ] T050 [P] Run `flake8 mcp_server/` and fix all E/W violations
- [ ] T051 [P] Run `pylint mcp_server/ --disable=C` and address all errors and warnings
- [ ] T052 [P] Run `bandit -r mcp_server/` and address any MEDIUM or HIGH severity findings
- [ ] T053 Validate quickstart.md: run `python -m mcp_server` and confirm it starts without error (process exits cleanly on EOF)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — ✅ complete
- **Foundational (Phase 2)**: Depends on Phase 1 — ✅ complete
- **US7 (Phase 3)**: Depends on Phase 2 — ✅ complete
- **US1 (Phase 4)**: Depends on Phase 2 — ✅ complete
- **US2 (Phase 5)**: Depends on Phase 2 — ✅ complete
- **US3 (Phase 6)**: Depends on Phase 3 — ✅ complete
- **US4 (Phase 7)**: Depends on Phase 3 — ✅ complete
- **US5 (Phase 8)**: Depends on Phase 3 — ⬜ partially complete (add_biller pending)
- **US6 (Phase 9)**: Depends on Phase 3 — ✅ complete
- **US8 (Phase 10)**: Depends on Phase 2 only (open signup — no token needed) — ⬜ not started
- **Polish (Phase 11)**: Depends on all phases completing

### Remaining Work Order

```
T030 → T031 → T032 → T033     (add_biller: tests → confirm fail → impl → confirm pass)
T040 → T041 → T042 → T043     (create_personal_account: same cycle)
T044 → T045 → T046 → T047     (create_business_account: same cycle)
All of the above → T048–T053   (polish and coverage)
```

### Parallel Opportunities

```
# Test writing (different files / non-conflicting classes):
T030  TestAddBiller in mcp_server/tests/test_bills.py
T040  TestCreatePersonalAccount in mcp_server/tests/test_creation.py

# create_business_account tests go in same file as T040 (write after T040):
T044  TestCreateBusinessAccount in mcp_server/tests/test_creation.py

# Implementation (different functions in server.py — safe to parallelise):
T032  add_biller in mcp_server/server.py
T042  create_personal_account in mcp_server/server.py
T046  create_business_account in mcp_server/server.py

# Polish tasks T050–T052 are independent and can run in parallel
```

---

## Implementation Strategy

### Remaining Work Only

1. **US5 — add_biller** (Phase 8, T030–T033): Extend `test_bills.py` → implement `add_biller` in `server.py`
2. **US8 — create_personal_account** (Phase 10, T040–T043): Create `test_creation.py` → implement in `server.py`
3. **US8 — create_business_account** (Phase 10, T044–T047): Extend `test_creation.py` → implement in `server.py`
4. **Polish** (Phase 11, T048–T053): Full test suite + coverage + lint + quickstart validation

### Red-Green-Refactor Mandate (Constitution Principle II)

For each remaining tool:
1. Write test(s) — they **MUST fail** (no implementation yet)
2. Run `pytest` to confirm failure
3. Implement the tool handler
4. Run `pytest` to confirm pass
5. Refactor if needed; confirm pass again

### Incremental Delivery

| Milestone | Status |
|---|---|
| Phase 1–2: Infrastructure | ✅ complete |
| + US7: Login | ✅ complete |
| + US1: Account queries | ✅ complete |
| + US2: Transaction history | ✅ complete |
| + US3: Transfers | ✅ complete |
| + US4: Deposit / withdraw | ✅ complete |
| + US5: List billers + pay bills | ✅ complete |
| + US5: add_biller | ⬜ pending |
| + US6: Business pending transactions | ✅ complete |
| + US8: Account creation (personal + business) | ⬜ pending |
| + Polish | ⬜ pending |

---

## Notes

- US8 is not in the original spec user stories 1–7; it was introduced via clarifications on 2026-05-26 (FR-022 to FR-026 for account creation; FR-027 to FR-029 extends US5 with `add_biller`)
- `add_biller` maps to US5 (not US8) because FR-027 extends bill-management; the category is stored in `Biller.name` (not `Biller.category`) — map `category` → `Biller.name` internally; use `b.get_name_display()` for `category_display` (see data-model.md)
- `create_business_account` handler must call `BusinessAccount.objects.get(pk=result["business_account_id"])` after `services.create_business_account_mock()` because that service returns only IDs and credentials, not `company_name`, `uen`, or `balance`
- `create_personal_account` zero-deposit guard: skip `services.deposit()` entirely when `initial_deposit == "0.00"` — `_mcp_validate_amount` rejects zero, so use a plain equality check before calling the validator
- `[P]` tasks operate on different files with no mutual dependencies
- All write tools (US3–US6) must test expired token, wrong-owner token, and invalid amount — not just the happy path
- Decimal amounts MUST always be serialised as strings (never `float`) to prevent floating-point rounding loss
- Token storage is in-memory only; restarting the server process invalidates all active sessions
- `MCP_SESSION_TIMEOUT_MINUTES` is read from `os.environ` at module import; default is 15
