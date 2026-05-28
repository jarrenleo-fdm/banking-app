# Implementation Plan: MCP API Key Authentication

**Branch**: `007-mcp-api-key-auth` | **Date**: 2026-05-28 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/007-mcp-api-key-auth/spec.md`

## Summary

Add user-owned API keys that can authenticate MCP clients without exposing account
passwords. The implementation extends the existing `accounts` app with API key
management models, forms, views, and templates; stores only hashed key secrets; displays
new secrets exactly once; records key lifecycle audit events; and adds an MCP
`login_with_api_key` tool that issues the same short-lived session tokens used by the
existing username/password MCP login. API-key sessions must inherit the owning user's
personal, manager, or authoriser permissions and must not change any money movement
business rules.

**Active tier: Prototype / Learning** — SQLite3 backend, local linting instead of
SonarQube CI (see Complexity Tracking). Before real users or real money, migrate to the
Production tier.

## Technical Context

**Language/Version**: Python 3.11+  
**Primary Dependencies**: Django 5.2, `mcp[cli]>=1.9,<2`, pytest, pytest-django  
**Storage**: SQLite3 prototype database with Django ORM migrations in `accounts/`  
**Testing**: pytest + pytest-django; focused `accounts/tests/` and `mcp_server/tests/` coverage  
**Target Platform**: Server-rendered Django web app plus stdio MCP server process  
**Project Type**: Existing monolithic Django application with a standalone MCP package  
**Performance Goals**: API key creation and revocation complete within 2 seconds; MCP API key login completes within 2 seconds under normal prototype load  
**Constraints**: API key secrets must never be stored or logged in plaintext; full secrets are shown once only; API-key sessions must follow existing MCP authorisation checks; money writes continue to delegate to `banking.services`; use no float arithmetic for monetary data  
**Scale/Scope**: Prototype with a maximum of 5 active API keys per user, personal users plus generated business manager and authoriser users, and one MCP server process per connected AI client

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|---|---|---|
| I — Security & Confidentiality | PASS | Secrets stored hashed only; one-time reveal; password confirmation for key creation; generic auth failure messages; no key secrets in logs, views, MCP responses, or audit records |
| II — Test-First Development | PASS | Tasks must start with failing tests for key forms/views/models and MCP API-key authentication before implementation |
| III — Code Quality Gates | RELAXED | Prototype tier: SonarQube CI is not provisioned; local flake8, pylint, bandit, and pytest remain required before handoff |
| IV — Auditability & Observability | PASS | API key creation, successful auth, failed auth, and revocation create non-sensitive audit records with actor, key identifier when known, action, outcome, and timestamp |
| V — Data Integrity & Transactional Consistency | PASS | This feature does not introduce new balance mutation logic; authenticated money writes continue through existing transactional banking services |

*Post-design re-check: PASS with the same Prototype/Learning relaxation for Principle III. The data model stores only hashes and metadata, MCP contracts preserve least-privilege authorisation, and revocation requires API-key-backed sessions to re-check key status before protected actions.*

## Project Structure

### Documentation (this feature)

```text
specs/007-mcp-api-key-auth/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── mcp-tools.md
│   └── views.md
└── tasks.md             # Phase 2 output (/speckit-tasks — not created by /speckit-plan)
```

### Source Code (repository root)

```text
accounts/
├── models.py            # AccountAPIKey, APIKeyAuditEvent
├── forms.py             # APIKeyCreateForm, APIKeyRevokeForm
├── views.py             # list/create/revoke API key views
├── urls.py              # profile API key routes
├── admin.py             # safe metadata-only admin visibility
├── migrations/          # schema migration for key and audit models
├── templates/accounts/
│   ├── api_keys.html
│   └── api_key_created.html
└── tests/
    ├── test_api_keys_models.py
    ├── test_api_keys_forms.py
    └── test_api_keys_views.py

mcp_server/
├── auth.py              # API-key-aware session context and revocation validation
├── server.py            # login_with_api_key tool and existing auth integration
└── tests/
    ├── test_api_key_auth.py
    └── test_auth.py     # existing session behavior updated for auth context

templates/
└── base.html            # navigation link to API keys if needed
```

**Structure Decision**: API key ownership and management belong in `accounts/` because
keys authenticate a `CustomUser`, not a monetary `Account` or `BusinessAccount`. MCP
changes stay in `mcp_server/` and reuse the existing session-token flow so write tools keep
their current owner and role checks.

## Implementation Guide

### Step 1 — Failing tests first

Create failing tests before implementation:

- `accounts/tests/test_api_keys_models.py`: secret hashing, one-time raw key generation,
  active-key count, revocation state, last-used update, audit event creation.
- `accounts/tests/test_api_keys_forms.py`: required key name, duplicate active name for
  same user, password confirmation, active-key limit, no raw secret on existing records.
- `accounts/tests/test_api_keys_views.py`: login required, create flow shows secret once,
  list hides secret, revoke blocks future use, user cannot manage another user's key.
- `mcp_server/tests/test_api_key_auth.py`: valid key login, invalid generic failure,
  revoked key rejection, wrong-owner write rejection, business manager/authoriser role
  inheritance, revocation invalidating API-key-backed protected actions.

### Step 2 — Data model and migration

Add `AccountAPIKey` and `APIKeyAuditEvent` to `accounts.models`, generate a migration, and
register safe metadata-only admin views. `AccountAPIKey` stores a public identifier, a
hash of the secret, user-visible name, owner, status timestamps, and last-used timestamp.
It never stores the raw secret. `APIKeyAuditEvent` stores non-sensitive security activity.

### Step 3 — Key service behavior

Keep key lifecycle helpers close to the model or in a small accounts-owned helper:

- `create_key(user, name)` returns `(key_record, raw_secret)` and records a creation audit.
- `verify_key(raw_secret)` returns the owning user and key record or raises a generic
  authentication failure; successful verification updates `last_used_at` and records audit.
- `revoke_key(key, actor)` sets `revoked_at`, records audit, and ensures future MCP
  authentication fails.
- Enforce 5 active keys per user and one active key with the same name per user.

### Step 4 — Web key management

Add authenticated account routes:

- `GET /accounts/api-keys/`: list current user's key metadata.
- `POST /accounts/api-keys/`: create a key after password confirmation.
- `POST /accounts/api-keys/<identifier>/revoke/`: revoke an active key owned by the
  current user after CSRF validation.

Templates should fit the existing server-rendered profile style and avoid putting the full
secret anywhere except the immediate one-time success response. Do not persist the raw
secret in sessions, messages, logs, or database fields.

### Step 5 — MCP authentication

Add `login_with_api_key(api_key: str)` to `mcp_server/server.py`. On success it issues the
same short-lived session token shape as `login`, plus safe metadata such as username and
auth method. On failure it returns `{"error": "Authentication failed."}`.

Extend `TokenStore` so token records can carry an `auth_method` and optional API key
identifier. Protected write-tool validation must continue to return the authenticated
username. For API-key-backed sessions, validation must confirm the key remains active
before allowing protected actions, so web revocation blocks active MCP sessions as well as
future logins.

### Step 6 — Preserve banking boundaries

Do not add API key handling to interactive account login. Do not let API keys bypass
existing write-tool checks. Personal actions must still compare the authenticated username
to the target username, and business approval actions must still verify the assigned
authoriser user.

### Step 7 — Verification

Run focused tests first:

```bash
pytest accounts/tests/test_api_keys_models.py accounts/tests/test_api_keys_forms.py accounts/tests/test_api_keys_views.py -v
pytest mcp_server/tests/test_api_key_auth.py mcp_server/tests/test_auth.py -v
```

Then run the broader suites:

```bash
pytest accounts/tests/ mcp_server/tests/ -v
python manage.py check
pre-commit run --all-files
```

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|---|---|---|
| Principle III (SonarQube) relaxed | Prototype/Learning tier; SonarQube infrastructure is not configured in this repository | Blocking planning on external CI infrastructure would not improve the local prototype. Local `flake8`, `pylint`, `bandit`, and pytest are the compensating controls. |

**Production Migration TODO**: Before real users or real money, migrate to PostgreSQL,
configure SonarQube CI, enforce production secret management for API key signing/hash
settings, add durable rate limiting for failed API key login attempts, and run
`python manage.py check --deploy`.
