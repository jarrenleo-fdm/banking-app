# Tasks: MCP API Key Authentication

**Input**: Design documents from `/specs/007-mcp-api-key-auth/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: Included because the constitution and plan require test-first development.

**Organization**: Tasks are grouped by user story so each story can be implemented and
tested as an independently demonstrable increment.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel with other [P] tasks in the same phase because it touches different files or only adds tests.
- **[Story]**: Maps a task to the user story from `spec.md`.
- Every task includes exact file paths.

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Prepare empty feature files and confirm the implementation surface.

- [X] T001 [P] Create API key model/form/view test placeholders in `accounts/tests/test_api_keys_models.py`, `accounts/tests/test_api_keys_forms.py`, and `accounts/tests/test_api_keys_views.py`
- [X] T002 [P] Create MCP API key auth test placeholder in `mcp_server/tests/test_api_key_auth.py`
- [X] T003 [P] Create API key management template placeholders in `accounts/templates/accounts/api_keys.html` and `accounts/templates/accounts/api_key_created.html`
- [X] T004 [P] Create accounts-owned API key helper module placeholder in `accounts/api_keys.py`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Add shared data structures that all API key stories depend on.

**Critical**: No user story implementation can be completed until this phase is complete.

- [X] T005 [P] Write failing model tests for `AccountAPIKey` fields, active-state properties, active key limit, duplicate active key names, and `APIKeyAuditEvent` safe fields in `accounts/tests/test_api_keys_models.py`
- [X] T006 Add `AccountAPIKey` and `APIKeyAuditEvent` models, constants, choices, constraints, and safe `__str__` methods in `accounts/models.py`
- [X] T007 Generate and review the API key schema migration in `accounts/migrations/0002_account_api_keys.py`
- [X] T008 Run `python manage.py migrate` and fix migration issues in `accounts/migrations/0002_account_api_keys.py`

**Checkpoint**: The database schema supports user-owned keys and non-sensitive audit events.

---

## Phase 3: User Story 1 - Generate API Key for MCP Access (Priority: P1) MVP

**Goal**: An authenticated user can create a named API key, confirm identity with their password, and see the full secret exactly once.

**Independent Test**: Sign in, create a key with a valid name and password, confirm the raw secret is displayed immediately, then return to the key list and confirm the full secret cannot be recovered.

### Tests for User Story 1

> Write these tests first and confirm they fail before implementation.

- [X] T009 [P] [US1] Write failing form tests for required name, duplicate active name, active-key limit, and password confirmation in `accounts/tests/test_api_keys_forms.py`
- [X] T010 [P] [US1] Write failing view tests for login-required access, successful key creation, one-time secret display, and hidden secret on later list view in `accounts/tests/test_api_keys_views.py`
- [X] T011 [P] [US1] Write failing helper tests for raw secret generation, identifier format, hashed storage, and no plaintext persistence in `accounts/tests/test_api_keys_models.py`

### Implementation for User Story 1

- [X] T012 [US1] Implement `create_key(user, name)` and secret hashing/comparison helpers in `accounts/api_keys.py`
- [X] T013 [US1] Implement `APIKeyCreateForm` with trimmed name validation, password confirmation, duplicate active-name validation, and active-key limit validation in `accounts/forms.py`
- [X] T014 [US1] Implement authenticated API key list/create view logic with one-time raw secret context in `accounts/views.py`
- [X] T015 [US1] Add `api_keys` route for `GET /accounts/api-keys/` and `POST /accounts/api-keys/` in `accounts/urls.py`
- [X] T016 [US1] Build key creation and metadata list UI without raw secret leakage in `accounts/templates/accounts/api_keys.html`
- [X] T017 [US1] Build immediate one-time secret display UI in `accounts/templates/accounts/api_key_created.html`
- [X] T018 [US1] Add a visible API key management link from the account profile page in `accounts/templates/accounts/profile.html`
- [X] T019 [US1] Run `pytest accounts/tests/test_api_keys_models.py accounts/tests/test_api_keys_forms.py accounts/tests/test_api_keys_views.py -v` and fix US1 failures in `accounts/api_keys.py`, `accounts/forms.py`, `accounts/views.py`, and `accounts/templates/accounts/`

**Checkpoint**: User Story 1 is fully functional and independently testable.

---

## Phase 4: User Story 2 - Authenticate to MCP Using an API Key (Priority: P1)

**Goal**: An MCP client can exchange a valid active API key for the same short-lived session token used by existing protected MCP tools.

**Independent Test**: Use a valid API key with `login_with_api_key`, then perform a protected action on the owner account; repeat with a wrong target account, malformed key, and revoked key to confirm safe rejection.

### Tests for User Story 2

> Write these tests first and confirm they fail before implementation.

- [X] T020 [P] [US2] Write failing TokenStore tests for `auth_method`, `api_key_identifier`, password-token compatibility, and revoked API-key session validation in `mcp_server/tests/test_auth.py`
- [X] T021 [P] [US2] Write failing MCP contract tests for `login_with_api_key` success output, generic failure output, malformed key rejection, and revoked key rejection in `mcp_server/tests/test_api_key_auth.py`
- [X] T022 [US2] Write failing MCP authorisation tests for API-key-backed wrong-owner personal actions and business authoriser approval inheritance in `mcp_server/tests/test_api_key_auth.py`

### Implementation for User Story 2

- [X] T023 [US2] Extend `TokenStore`, token records, `issue_token`, and `validate_token` to carry auth context and re-check active API keys in `mcp_server/auth.py`
- [X] T024 [US2] Implement `verify_key(raw_secret)` and generic API key authentication failure handling in `accounts/api_keys.py`
- [X] T025 [US2] Add `login_with_api_key(api_key: str)` MCP tool with the contract output shape in `mcp_server/server.py`
- [X] T026 [US2] Update existing password `login` token issuance to use the new password auth context in `mcp_server/server.py`
- [X] T027 [US2] Keep protected MCP write tools routed through `_auth(session_token)` so API-key sessions inherit existing owner and role checks in `mcp_server/server.py`
- [X] T028 [US2] Run `pytest mcp_server/tests/test_api_key_auth.py mcp_server/tests/test_auth.py -v` and fix US2 failures in `mcp_server/auth.py`, `mcp_server/server.py`, and `accounts/api_keys.py`

**Checkpoint**: User Story 2 works without changing existing password MCP login behavior.

---

## Phase 5: User Story 3 - Manage Existing API Keys (Priority: P2)

**Goal**: A user can review key metadata, revoke an active key, and create a replacement without exposing any stored secret.

**Independent Test**: Create two keys, revoke one, confirm that only the revoked key stops authenticating while the other active key still works and the list shows safe metadata.

### Tests for User Story 3

> Write these tests first and confirm they fail before implementation.

- [X] T029 [P] [US3] Write failing view tests for metadata list fields, active-only revoke controls, already-revoked handling, and cross-user 404 behavior in `accounts/tests/test_api_keys_views.py`
- [X] T030 [P] [US3] Write failing helper tests for `revoke_key`, replacement flow, revoked-key state, and other-key preservation in `accounts/tests/test_api_keys_models.py`
- [X] T031 [P] [US3] Write failing MCP tests proving revoked keys cannot log in and API-key-backed sessions from revoked keys are invalidated in `mcp_server/tests/test_api_key_auth.py`

### Implementation for User Story 3

- [X] T032 [US3] Implement `revoke_key(key, actor)` and replacement-safe active-key counting in `accounts/api_keys.py`
- [X] T033 [US3] Add model methods or properties needed for revocation state and safe metadata display in `accounts/models.py`
- [X] T034 [US3] Implement revoke POST handling, owner-only lookup, already-revoked messaging, and redirect behavior in `accounts/views.py`
- [X] T035 [US3] Add `api_key_revoke` route for `POST /accounts/api-keys/<identifier>/revoke/` in `accounts/urls.py`
- [X] T036 [US3] Update metadata list, last-used display, revoked-date display, and active-key revoke controls in `accounts/templates/accounts/api_keys.html`
- [X] T037 [US3] Run `pytest accounts/tests/test_api_keys_models.py accounts/tests/test_api_keys_views.py mcp_server/tests/test_api_key_auth.py -v` and fix US3 failures in `accounts/api_keys.py`, `accounts/models.py`, `accounts/views.py`, `accounts/urls.py`, `accounts/templates/accounts/api_keys.html`, and `mcp_server/auth.py`

**Checkpoint**: User Story 3 is independently usable after User Story 1 and preserves User Story 2 authentication safety.

---

## Phase 6: User Story 4 - Audit API Key Activity (Priority: P3)

**Goal**: Key creation, successful authentication, failed authentication, and revocation are traceable without exposing key secrets.

**Independent Test**: Create, use, fail to use, and revoke API keys, then verify audit events contain actor/key/action/outcome/timestamp and no raw secret material.

### Tests for User Story 4

> Write these tests first and confirm they fail before implementation.

- [X] T038 [P] [US4] Write failing audit event tests for created and revoked lifecycle events with no raw secret values in `accounts/tests/test_api_keys_models.py`
- [X] T039 [P] [US4] Write failing MCP audit tests for `AUTH_SUCCESS`, `AUTH_FAILURE`, generic failure categories, and no raw secret values in `mcp_server/tests/test_api_key_auth.py`
- [X] T040 [P] [US4] Write failing admin safety tests for metadata-only `AccountAPIKey` and `APIKeyAuditEvent` admin display in `accounts/tests/test_api_keys_views.py`

### Implementation for User Story 4

- [X] T041 [US4] Add audit event creation for key creation, successful verification, failed verification, and revocation in `accounts/api_keys.py`
- [X] T042 [US4] Register metadata-only admin classes for `AccountAPIKey` and `APIKeyAuditEvent` without `secret_hash` editing or raw secret display in `accounts/admin.py`
- [X] T043 [US4] Ensure MCP authentication failure paths record safe audit categories without leaking identifiers or raw secrets in `mcp_server/server.py`
- [X] T044 [US4] Run `pytest accounts/tests/test_api_keys_models.py accounts/tests/test_api_keys_views.py mcp_server/tests/test_api_key_auth.py -v` and fix US4 failures in `accounts/api_keys.py`, `accounts/admin.py`, and `mcp_server/server.py`

**Checkpoint**: User Story 4 provides a non-sensitive audit trail for API key lifecycle and authentication activity.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Validate the whole feature, harden security boundaries, and update operational notes.

- [X] T045 [P] Add or update API key setup instructions and revocation verification notes in `README.md`
- [X] T046 [P] Add API key MCP usage notes to the active agent guide in `AGENTS.md`
- [X] T047 Review all templates and messages for accidental raw secret persistence or display in `accounts/templates/accounts/api_keys.html`, `accounts/templates/accounts/api_key_created.html`, and `accounts/views.py`
- [X] T048 Run `pytest accounts/tests/ mcp_server/tests/ -v` and fix regressions in `accounts/` and `mcp_server/`
- [X] T049 Run `python manage.py check` and fix Django system check issues in `accounts/`, `banking/`, `banking_app/`, and `mcp_server/`
- [X] T050 Run `pre-commit run --all-files` and fix lint/security findings in files touched by this feature using `.pre-commit-config.yaml`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 Setup**: No dependencies; can start immediately.
- **Phase 2 Foundational**: Depends on Phase 1; blocks all user stories because the models and migration are shared.
- **Phase 3 US1**: Depends on Phase 2; creates the key generation surface and is the MVP.
- **Phase 4 US2**: Depends on US1 because MCP authentication needs generated active keys.
- **Phase 5 US3**: Depends on US1 and US2 because revocation must affect both key management and MCP sessions.
- **Phase 6 US4**: Depends on US1, US2, and US3 so all lifecycle events exist before audit completion.
- **Phase 7 Polish**: Depends on the desired user stories being complete.

### User Story Dependencies

- **US1 Generate API Key (P1)**: First independently demonstrable slice after foundation.
- **US2 Authenticate to MCP (P1)**: Requires US1-generated keys, but preserves existing password login as a fallback.
- **US3 Manage Existing API Keys (P2)**: Requires US1 key records and US2 authentication behavior to verify revoked-session blocking.
- **US4 Audit API Key Activity (P3)**: Requires lifecycle/authentication events from US1-US3.

### Within Each User Story

- Tests must be written and fail before implementation.
- Model/helper tasks precede form, view, template, and MCP integration tasks.
- Story validation commands run at each checkpoint before moving to the next story.

## Parallel Execution Examples

### User Story 1

```text
Task: "Write failing form tests for required name, duplicate active name, active-key limit, and password confirmation in accounts/tests/test_api_keys_forms.py"
Task: "Write failing view tests for login-required access, successful key creation, one-time secret display, and hidden secret on later list view in accounts/tests/test_api_keys_views.py"
Task: "Write failing helper tests for raw secret generation, identifier format, hashed storage, and no plaintext persistence in accounts/tests/test_api_keys_models.py"
```

### User Story 2

```text
Task: "Write failing TokenStore tests for auth_method, api_key_identifier, password-token compatibility, and revoked API-key session validation in mcp_server/tests/test_auth.py"
Task: "Write failing MCP contract tests for login_with_api_key success output, generic failure output, malformed key rejection, and revoked key rejection in mcp_server/tests/test_api_key_auth.py"
```

### User Story 3

```text
Task: "Write failing view tests for metadata list fields, active-only revoke controls, already-revoked handling, and cross-user 404 behavior in accounts/tests/test_api_keys_views.py"
Task: "Write failing helper tests for revoke_key, replacement flow, revoked-key state, and other-key preservation in accounts/tests/test_api_keys_models.py"
Task: "Write failing MCP tests proving revoked keys cannot log in and API-key-backed sessions from revoked keys are invalidated in mcp_server/tests/test_api_key_auth.py"
```

### User Story 4

```text
Task: "Write failing audit event tests for created and revoked lifecycle events with no raw secret values in accounts/tests/test_api_keys_models.py"
Task: "Write failing MCP audit tests for AUTH_SUCCESS, AUTH_FAILURE, generic failure categories, and no raw secret values in mcp_server/tests/test_api_key_auth.py"
Task: "Write failing admin safety tests for metadata-only AccountAPIKey and APIKeyAuditEvent admin display in accounts/tests/test_api_keys_views.py"
```

## Implementation Strategy

### MVP First

1. Complete Phase 1 and Phase 2.
2. Complete Phase 3 (US1) only.
3. Validate that a signed-in user can create a named API key and see the secret once.
4. Stop for review or continue to MCP authentication.

### Incremental Delivery

1. US1 delivers secure key generation.
2. US2 makes generated keys useful for MCP authentication.
3. US3 gives users safe rotation and revocation.
4. US4 completes auditability for the security lifecycle.

### Parallel Team Strategy

After Phase 2, one engineer can implement US1 while another starts US2 test design against
the contract. US3 and US4 should wait for US1/US2 behavior to settle because revocation
and audit assertions depend on concrete lifecycle events.

## Notes

- Keep API key secrets out of logs, messages, sessions, templates after creation, admin displays, and MCP success/error payloads after authentication.
- Preserve existing username/password MCP login and all protected write-tool authorisation checks.
- Do not add API key support to interactive web login.
- Do not touch unrelated dirty worktree files except where a listed task requires it.
