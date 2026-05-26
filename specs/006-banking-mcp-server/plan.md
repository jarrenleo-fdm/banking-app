# Implementation Plan: Banking MCP Server

**Branch**: `006-banking-mcp-server` | **Date**: 2026-05-25 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/006-banking-mcp-server/spec.md`

## Summary

Build a standalone MCP server using the official MCP Python SDK (FastMCP, stdio transport)
that exposes 16 tools giving AI models read and write access to the banking app's Django
database. Write tools require a session token obtained via a `login` tool; account creation
tools are unauthenticated (open signup); read tools are public. The server delegates all
financial operations to the existing `banking.services` module and adds only a thin MCP-layer
for authentication, authorisation, input validation, and JSON serialisation.

**Active tier: Prototype / Learning** — SQLite3 backend, local linting instead of
SonarQube CI (see Complexity Tracking).

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: Django 5.2, `mcp[cli]>=1.9,<2` (FastMCP, stdio transport)
**Storage**: SQLite3 (existing `db.sqlite3`; shared with the Django app)
**Testing**: pytest + pytest-django (existing project toolchain)
**Target Platform**: Desktop / server AI agent environments (Claude Desktop, Cursor, etc.)
**Project Type**: Standalone MCP server process (not a Django app or web service)
**Performance Goals**: Each tool call < 2 s under normal load (SC-001)
**Constraints**: Monetary values use `Decimal`; no floating-point math
**Scale/Scope**: Single-user prototype; one server process per AI agent session

## Constitution Check

*GATE: Must pass before implementation. Re-checked after Phase 1 design.*

| Principle | Status | Notes |
|---|---|---|
| I — Security | ✅ PASS | Session tokens; least-privilege auth; no secrets committed; amounts validated |
| II — Test-First | ✅ PASS | Red-Green-Refactor cycle required; all money paths need unit + integration tests |
| III — SonarQube | ⚠ RELAXED | Prototype tier: flake8 + pylint + bandit run locally instead (see Complexity Tracking) |
| IV — Auditability | ✅ PASS | All writes go through existing services which create immutable Transaction records |
| V — Data Integrity | ⚠ RELAXED | Prototype tier / SQLite3: `@transaction.atomic` used instead of `select_for_update` (see Complexity Tracking) |

*Re-evaluated post-Phase-1 design: no status changes. The 3 new tools (`create_personal_account`, `create_business_account`, `add_biller`) fit existing patterns — each is either wrapped in `@transaction.atomic` or delegates to an existing atomic service.*

## Project Structure

### Documentation (this feature)

```text
specs/006-banking-mcp-server/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/
│   └── tool-schemas.md  # Phase 1 output
└── tasks.md             # Phase 2 output (/speckit-tasks — not yet created)
```

### Source Code

```text
mcp_server/
├── __init__.py          # entry point: sets DJANGO_SETTINGS_MODULE, calls django.setup(), runs server
├── server.py            # FastMCP instance; all 16 @mcp.tool() registrations
├── auth.py              # TokenStore, login validation, token issue/validate/expire
├── utils.py             # _mcp_validate_amount (positivity + 2 d.p.)
└── tests/
    ├── __init__.py
    ├── conftest.py       # Django DB fixtures shared across test modules
    ├── test_auth.py      # login, token expiry, re-use of expired token
    ├── test_accounts.py  # get_account, get_business_account
    ├── test_transactions.py  # list_transactions, list_business_transactions
    ├── test_transfers.py     # transfer_funds, deposit_funds, withdraw_funds
    ├── test_bills.py         # list_billers, pay_bill, add_biller
    ├── test_business.py      # list_pending_transactions, approve_transaction, reject_transaction
    └── test_creation.py      # create_personal_account, create_business_account
```

**Structure Decision**: `mcp_server/` lives at the repo root as a plain Python package.
It is **not** added to `INSTALLED_APPS`; it has no migrations. It calls `django.setup()`
once in `__init__.py` so that Django ORM is available when the FastMCP server starts.

## Implementation Guide

### Step 1 — Auth layer (`mcp_server/auth.py`)

Implement `TokenStore` (in-memory `dict[str, TokenRecord]`) with:
- `issue_token(username) -> str` — generates a 32-byte hex token, stores `TokenRecord`
- `validate_token(token) -> str` — returns username or raises `SessionExpiredError`; slides `last_used`
- `_purge_expired()` — called on each validate; removes stale entries

`MCP_SESSION_TIMEOUT_MINUTES` read from `os.environ`, defaulting to `15`.

### Step 2 — Utility helpers (`mcp_server/utils.py`)

`_mcp_validate_amount(amount: str) -> Decimal`:
- Parses string to `Decimal` (catches `InvalidOperation`)
- Checks `> 0` and `== quantize("0.01")`
- Raises `ValueError` with a clear message on failure

### Step 3 — Server and tools (`mcp_server/server.py`)

Create a `FastMCP("banking")` instance. Register all 16 tools with `@mcp.tool()`.

**Tool registration order** (open tools first, then read tools, then auth, then write tools):
1. `create_personal_account` *(open signup — no token)*
2. `create_business_account` *(open signup — no token)*
3. `get_account`
4. `get_business_account`
5. `list_transactions`
6. `list_business_transactions`
7. `list_billers`
8. `list_pending_transactions`
9. `login`
10. `deposit_funds`
11. `withdraw_funds`
12. `transfer_funds`
13. `pay_bill`
14. `add_biller`
15. `approve_transaction`
16. `reject_transaction`

Each tool handler:
- Calls `_mcp_validate_amount` for write tools (before any DB access)
- Calls `token_store.validate_token(session_token)` for write tools
- Verifies the token owner matches the target account (authorisation)
- Delegates to the appropriate `banking.services` function
- Returns a plain `dict` (FastMCP serialises it to JSON)
- Catches domain exceptions and returns `{"error": "<message>"}`

**`create_personal_account`** (FR-023):
- Accepts: `name`, `username`, `email`, `phone_number`, `password`, optional `initial_deposit` (Decimal string, default "0.00")
- Wraps `CustomUser.objects.create_user(...)` + optional `services.deposit(user.account, amt)` in `@transaction.atomic`
- Validates `initial_deposit >= 0` via `_mcp_validate_amount` (or zero-amount guard)
- Returns `username`, `name`, `balance`, `created_at`
- Note: `name`, `email`, and `phone_number` are required by the `CustomUser` model (mirrors the web signup form); the spec's abbreviated field list is for brevity

**`create_business_account`** (FR-024, FR-025, FR-026):
- Accepts: `company_name`, `uen`, `street`, `city`, `postal_code`, optional `initial_deposit` (Decimal string, default "7000.00")
- Delegates to `services.create_business_account_mock(...)` (enforces 7000 minimum, UEN uniqueness, atomicity)
- The service returns only IDs and credentials; handler fetches `BusinessAccount.objects.get(pk=result["business_account_id"])` to populate `company_name`, `uen`, and `balance` in the response
- Catches `IntegrityError` for duplicate UEN (raised by the DB before the service-level check fires in some paths)
- Returns: `company_name`, `uen`, `balance`, `manager_username`, `manager_password`, `manager_phone`, `authoriser_username`, `authoriser_password`, `authoriser_phone`

**`add_biller`** (FR-027, FR-028, FR-029):
- Accepts: `session_token`, `category` (one of 5 string values from `Biller.BILLER_CATEGORIES`), `reference`
- Validates `category` against `Biller.BILLER_CATEGORIES` key list
- Creates `Biller(account=acct, name=category, reference=reference)` and calls `.save()`
- Catches `IntegrityError` for duplicate (account, name, reference) constraint
- Returns: `id`, `category`, `category_display`, `reference`, `created_at`

### Step 4 — Entry point (`mcp_server/__init__.py`)

```python
import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "banking_app.settings")
import django
django.setup()
from .server import mcp

def main():
    mcp.run()

if __name__ == "__main__":
    main()
```

### Step 5 — Tests (`mcp_server/tests/`)

Follow Red-Green-Refactor. For each tool:
1. Write test(s) that fail (no implementation yet)
2. Implement the tool handler
3. Confirm tests pass
4. Refactor if needed

Test each acceptance scenario from the spec, plus:
- Expired token rejected on all write tools
- Wrong-owner token rejected
- Non-authoriser token rejected on approve/reject
- Zero / negative amount rejected
- More than 2 decimal places rejected
- Non-existent account returns clear error
- `create_personal_account`: duplicate username returns error; initial_deposit < 0 rejected
- `create_business_account`: initial_deposit < 7000 rejected; duplicate UEN rejected; returned credentials are valid (can authenticate with `login`)
- `add_biller`: invalid category rejected; duplicate (category + reference) rejected; no-token call rejected

### Step 6 — Add dependency

Add `mcp[cli]>=1.9,<2` to `requirements.txt`.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|---|---|---|
| Principle III (SonarQube) relaxed | Prototype/Learning tier — SonarQube infra not provisioned | Running SonarQube locally for a prototype adds infra overhead not warranted. flake8 + pylint + bandit compensate. |
| Principle V (`select_for_update`) relaxed | SQLite3 backend used | SQLite3 does not support row-level locking. `@transaction.atomic` issues an exclusive write lock on the whole DB, preventing concurrent corruption at this scale. |

**Production Migration TODO**: Before real users or real money, migrate to PostgreSQL,
enable `select_for_update()` on all balance-modifying paths, and configure SonarQube CI.
