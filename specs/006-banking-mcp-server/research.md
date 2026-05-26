# Research: Banking MCP Server

## 1. MCP Python SDK

**Decision**: Use `FastMCP` from the `mcp` package (decorator-based API).

**Rationale**: FastMCP is the idiomatic high-level interface provided by the official SDK.
It reduces tool registration to a single `@mcp.tool()` decorator and handles JSON Schema
generation from Python type annotations automatically. The low-level `Server` class is
unnecessary here since we have no streaming or resource needs beyond tool calls.

**Transport**: `stdio` — the standard transport for desktop and server-side AI agents
(Claude Desktop, Cursor, etc.). The server process is launched by the AI client with its
stdin/stdout wired to the MCP JSON-RPC channel.

**Version pin**: `mcp[cli]>=1.9,<2` (current stable series; `[cli]` includes `fastmcp`).

**Alternatives considered**:
- Low-level `Server` class — more verbose, no advantage for a pure tool server.
- HTTP/SSE transport — not needed; stdio covers all target environments.

---

## 2. Django ORM in a Standalone Process

**Decision**: The MCP server is a standalone Python package (`mcp_server/`) that calls
`django.setup()` at import time via the entry point.

**Rationale**: The spec requires the MCP server to share the same database as the banking
app. A standalone process that configures Django settings and calls `django.setup()` gets
full ORM access without becoming a Django "app" (no migrations, no views, not listed in
`INSTALLED_APPS`).

**Entry point pattern**:
```python
import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "banking_app.settings")
import django
django.setup()
# only then import models / services
```

**Alternatives considered**:
- A new Django management command — would require running through `manage.py`, complicating
  stdio transport setup.
- A separate microservice that calls the banking app's HTTP endpoints — explicitly out of
  scope per spec Assumptions.

---

## 3. Identifier Mapping: Username vs Phone Number

**Decision**: MCP tools accept `username` as the account identifier for personal accounts.
The MCP layer resolves usernames to `Account` objects (and phone numbers where needed)
before delegating to `banking.services`.

**Rationale**: Read tools (FR-001) already key on username. Using username everywhere gives
models a single consistent identifier. The existing `services.transfer()` accepts
`recipient_phone`; the MCP `transfer_funds` tool will look up the recipient by username and
extract their phone number to pass to the service.

**Lookup path**: `User.objects.get(username=...) → user.account` for personal accounts;
`BusinessAccount.objects.get(uen=...)` or `get(company_name__iexact=...)` for business.

---

## 4. FR-015 vs. FR-016/017/021 — Stateless Server + Session Tokens

**Decision**: Interpret FR-015 as "no banking domain state is retained between calls" (no
pending cart, no multi-step wizard). Session tokens are an orthogonal security mechanism
required by FR-016 through FR-021 and are explicitly part of the spec.

**Implementation**: An in-memory token store — a plain Python `dict[str, TokenRecord]`
held in the server process — is sufficient for the Prototype tier. Tokens expire after
**15 minutes** of inactivity (sliding window on last successful use). This value is a
configuration constant `MCP_SESSION_TIMEOUT_MINUTES` in the server module.

**Why 15 minutes**: Standard short-lived web session default; short enough to limit
exposure if a token is captured, long enough for a typical AI agent task.

**Alternatives considered**:
- Django cache backend (Redis/Memcache) — production-grade but introduces an external
  dependency not warranted at prototype tier.
- Django database sessions — durable across restarts but adds DB writes for every read-tool
  call; rejected as over-engineering for this tier.

---

## 5. Decimal Validation (FR-013)

**Decision**: A thin `_validate_amount(amount: Decimal)` wrapper in the MCP server layer
enforces the two-decimal-places rule before delegating to `banking.services`.

**Rationale**: The existing `banking.services._validate_amount` only checks positivity.
Adding the decimal-places check there would touch tested, production service code beyond
the scope of this feature. A separate MCP-layer validator avoids that risk.

**Implementation**:
```python
def _mcp_validate_amount(amount: Decimal) -> None:
    if amount <= 0:
        raise ValueError("Amount must be greater than zero.")
    if amount != amount.quantize(Decimal("0.01")):
        raise ValueError("Amount must have at most two decimal places.")
```

---

## 6. Pending Transaction Creation — Scope Boundary

**Decision**: The MCP server exposes `list_pending_transactions`, `approve_transaction`,
and `reject_transaction` only. Creating pending transactions (withdrawal, transfer, bill
payment) is **out of scope** for v1.

**Rationale**: The spec (User Story 6) explicitly frames the MCP role as that of an
*authoriser*: listing, approving, and rejecting. Business managers create pending
transactions through the existing web UI. This is not an omission; it is the intended
boundary.

---

## 7. `create_personal_account` Required Fields

**Decision**: The `create_personal_account` tool accepts `name`, `username`, `email`,
`phone_number`, `password`, and optional `initial_deposit` — matching the web signup form.

**Rationale**: FR-023 says "accepts a username, password, and an optional initial deposit"
as a shorthand. However, `accounts.CustomUser` (model) has four required unique fields:
`username`, `email`, `name`, and `phone_number`. Omitting any would make account creation
impossible. The MCP tool mirrors the web form fields exactly.

**Implication**: `initial_deposit` validation uses `amount >= 0`; the existing
`_mcp_validate_amount` checks `amount > 0`, so a small guard (`amount == 0` bypasses the
service call) is added in the tool handler rather than changing the shared validator.

**Alternatives considered**:
- Auto-generate email/phone (like `create_business_account_mock`) — inappropriate for a
  "real" personal user who would need to receive communications or log in later.

---

## 9. Testing Approach

**Decision**: pytest + pytest-django, following the existing project convention.

- Unit tests cover tool handler functions with mocked services.
- Integration tests hit the SQLite3 test database (same DB used by existing tests).
- Test file location: `mcp_server/tests/`.

**Coverage target**: 80 % on new code (Principle III gate, Prototype tier).
