# Implementation Plan: Personal Banking MCP Server

**Branch**: `006-banking-mcp-server` | **Date**: 2026-05-28 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/006-banking-mcp-server/spec.md`

## Summary

Revise the standalone MCP server into a personal-banking-only tool surface authenticated
exclusively through account-owned API keys. The server exposes 10 tools: one open personal
signup tool, one API-key login tool, and eight protected personal account tools for account
summary, transactions, billers, deposits, withdrawals, transfers, adding billers, and bill
payments. All business account tools and username/password MCP login are removed.

The implementation remains a thin MCP layer over the existing Django banking app. It reuses
the API key lifecycle from `specs/007-mcp-api-key-auth/`, validates every protected call with
a short-lived API-key-backed session token, re-checks API key revocation before returning
private data or changing balances, and delegates money movements to existing banking services.

**Active tier: Prototype / Learning** - SQLite3 backend, local linting instead of SonarQube
CI, and no production deployment assumptions.

## Technical Context

**Language/Version**: Python 3.11+  
**Primary Dependencies**: Django 5.2, `mcp[cli]>=1.9,<2`, pytest, pytest-django  
**Storage**: SQLite3 prototype database shared with the Django app; no new 006 migrations  
**Testing**: pytest + pytest-django; MCP-focused tests in `mcp_server/tests/`  
**Target Platform**: Desktop/server AI agent environments using MCP stdio transport  
**Project Type**: Existing Django monolith with a standalone `mcp_server/` Python package  
**Performance Goals**: API-key login and common personal account tool calls complete in under 2 seconds under normal local conditions  
**Constraints**: API-key-only MCP login; no business MCP tools; protected reads and writes require a valid session token; money uses `Decimal`; no float arithmetic; all failures leave balances, billers, and transactions unchanged  
**Scale/Scope**: Prototype, one MCP server process per AI client session, 10 supported personal MCP tools

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|---|---|---|
| I - Security & Confidentiality | PASS | MCP login is API-key-only; protected reads and writes validate sessions; raw API keys are never returned after login; revoked keys invalidate active sessions. |
| II - Test-First Development | PASS | Tasks must preserve red-green-refactor; every protected read/write and money path requires failing tests before implementation. |
| III - Code Quality Gates | RELAXED | Prototype/Learning tier: SonarQube CI is not configured; compensate with local pytest, flake8, pylint, and bandit before handoff. |
| IV - Auditability & Observability | PASS | API key auth events are handled by the 007 API key feature; money writes use existing services that create immutable personal transactions. |
| V - Data Integrity & Transactional Consistency | RELAXED | SQLite3 prototype tier permits `@transaction.atomic` instead of row-level locking; existing services remain the balance mutation boundary. |

*Post-design re-check: PASS with the same Prototype/Learning relaxations for Principle III
and the SQLite-specific row-locking portion of Principle V. The design removes public reads,
removes business tools from the MCP surface, and keeps money mutations delegated to existing
transactional services.*

## Project Structure

### Documentation (this feature)

```text
specs/006-banking-mcp-server/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── tool-schemas.md
└── tasks.md             # Phase 2 output from /speckit-tasks
```

### Source Code (repository root)

```text
accounts/
├── api_keys.py          # existing API-key create/verify/revoke helpers from 007
├── models.py            # CustomUser, AccountAPIKey, APIKeyAuditEvent
├── forms.py             # existing signup and API-key forms
└── validators.py        # password and phone validation helpers

banking/
├── models.py            # Account, Transaction, Biller
└── services.py          # deposit, withdraw, transfer, pay_bill service boundary

mcp_server/
├── __init__.py          # Django setup and mcp.run() entry point
├── __main__.py          # python -m mcp_server entry point
├── auth.py              # API-key-backed session token store
├── server.py            # FastMCP instance and 10 personal tool registrations
├── utils.py             # MCP amount and input validation helpers
└── tests/
    ├── conftest.py
    ├── test_api_key_auth.py
    ├── test_auth.py
    ├── test_accounts.py
    ├── test_transactions.py
    ├── test_transfers.py
    ├── test_bills.py
    └── test_creation.py
```

**Structure Decision**: `mcp_server/` remains a plain Python package at the repository root,
not a Django app and not part of `INSTALLED_APPS`. API key ownership and lifecycle stay in
`accounts/`; personal money movement stays in `banking.services`; the MCP layer owns only
tool registration, session validation, authorisation, input validation, and JSON-friendly
serialization.

## Implementation Guide

### Step 1 - Align the tool surface

Remove MCP registrations and tests for:

- `login`
- `get_business_account`
- `list_business_transactions`
- `list_pending_transactions`
- `approve_transaction`
- `reject_transaction`
- `create_business_account`

The supported 006 tool list is:

1. `create_personal_account` - open signup
2. `login_with_api_key` - open authentication
3. `get_account` - protected
4. `list_transactions` - protected
5. `list_billers` - protected
6. `deposit_funds` - protected
7. `withdraw_funds` - protected
8. `transfer_funds` - protected
9. `add_biller` - protected
10. `pay_bill` - protected

### Step 2 - Session validation

`mcp_server.auth.TokenStore` issues short-lived session tokens only from
`login_with_api_key`. Token records include:

- username
- auth method, fixed to `api_key`
- API key identifier
- last-used timestamp

Every protected tool calls the shared validation helper before reading private data or
performing writes. Validation purges expired tokens and confirms the backing API key is
still active so revocation blocks future protected actions as well as future logins.

### Step 3 - Protected personal account helpers

Protected tools derive the target account from the session user. They do not accept a target
username for account summary, transactions, billers, deposits, withdrawals, or bill payments.
Transfers accept a recipient phone number only, matching the core banking recipient model.

### Step 4 - Input validation

MCP amount inputs are strings parsed to `Decimal`. Deposit, withdrawal, transfer, and bill
payment amounts must be positive and have at most two decimal places. Personal signup
initial balance may be omitted or zero; positive values must also have at most two decimal
places. Invalid input returns structured `{"error": "..."}` dictionaries before database
state changes.

### Step 5 - Personal signup

`create_personal_account` mirrors the web signup data requirements: name, username, email,
phone number, password, and optional initial balance. It must enforce username/email/phone
uniqueness, Singapore-style phone validation, password complexity, and atomic account
creation. It must not create or return an API key.

### Step 6 - Tests and verification

Use pytest and pytest-django. Each story's tests must be written first, confirmed failing,
implemented, then rerun to pass. The final verification set is:

```bash
pytest mcp_server/tests/ -v
pytest mcp_server/tests/ --cov=mcp_server --cov-report=term-missing
python manage.py check
flake8 mcp_server/
pylint mcp_server/ --disable=C
bandit -r mcp_server/
```

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|---|---|---|
| Principle III relaxed | Prototype/Learning tier does not have SonarQube CI configured | Blocking the prototype on external CI infrastructure is disproportionate; local pytest, flake8, pylint, and bandit compensate. |
| Principle V row-level locking relaxed | SQLite3 backend does not support row-level locking | Existing balance-modifying services use transactions; SQLite serializes writes at this prototype scale. |

**Production Migration TODO**: Before real users or real money, migrate to PostgreSQL,
enable row-level locking for balance mutations, configure SonarQube CI, enforce production
secret management, enable HTTPS and secure cookies, add durable rate limiting for API-key
login failures, and run `python manage.py check --deploy`.
