# Research: Personal Banking MCP Server

## 1. API-Key-Only MCP Authentication

**Decision**: `login_with_api_key` is the only MCP login tool. Username-and-password MCP
login is removed from the 006 tool surface.

**Rationale**: The overhauled spec requires MCP clients to authenticate without receiving
or storing account passwords. API keys are user-owned, revocable, and already covered by
the API-key feature's one-time secret display, hashing, last-used metadata, and audit
events.

**Alternatives considered**:
- Keep `login(username, password)` beside API keys - rejected because the spec explicitly
  allows logins only through API keys.
- Accept API keys directly on every protected tool - rejected because short-lived session
  tokens reduce repeated exposure of the raw API key.

## 2. Protected Reads

**Decision**: Account summary, transaction listing, and biller listing require a valid
API-key-backed session token.

**Rationale**: Personal balances, transaction history, and billers are private banking data.
The old public-read MCP behavior conflicts with the revised specification and with least
privilege.

**Alternatives considered**:
- Keep public reads for convenience - rejected because it lets any MCP client query private
  account data.
- Require tokens only for writes - rejected because transaction history and biller metadata
  reveal sensitive financial behavior.

## 3. Personal-Only MCP Tool Surface

**Decision**: Remove all MCP business account tools from this feature. The 006 tool surface
contains only personal account tools plus open personal signup and API-key login.

**Rationale**: Business accounts have separate manager/authoriser workflows and approval
rules. The revised spec intentionally narrows MCP access to personal banking.

**Alternatives considered**:
- Keep read-only business tools - rejected because the user requested all business account
  tools be removed.
- Keep authoriser approval tools - rejected because business approval is out of scope for
  this MCP feature after the overhaul.

## 4. Target Account Resolution

**Decision**: Protected personal tools derive the account from the authenticated session
user instead of accepting a username or account identifier.

**Rationale**: Deriving the target account from the token eliminates wrong-owner inputs for
reads and self-service writes. It directly enforces "operate only on my own account" at the
MCP boundary.

**Alternatives considered**:
- Keep `username` on protected tools and compare it to the token owner - workable, but
  more error-prone and leaks a user-enumeration shaped interface.
- Accept account IDs - rejected because personal users do not need to know internal IDs and
  the existing domain model is user/account-centric.

## 5. Transfer Recipient Identifier

**Decision**: `transfer_funds` accepts `recipient_phone`, not recipient username.

**Rationale**: Core banking specifies phone-number recipient lookup. The MCP contract should
match the user-facing banking behavior and avoid maintaining a separate recipient identity
model.

**Alternatives considered**:
- Transfer by username - rejected because it diverges from the core banking specification.
- Transfer by account ID - rejected because internal account IDs are not user-facing.

## 6. Session Token Store and Revocation

**Decision**: Continue using an in-memory token store for prototype sessions, but every
token stores the backing API key identifier and validates that the key remains active.
Tokens expire after 15 minutes of inactivity by default.

**Rationale**: The prototype already runs one MCP server process per connected client. A
sliding in-memory token is sufficient locally, while the backing key check ensures web
revocation immediately blocks protected MCP actions from existing sessions.

**Alternatives considered**:
- Persist MCP sessions in the database - rejected for prototype scope and because the raw
  API key is not stored in tokens.
- Cache sessions in Redis - production-grade, but introduces infrastructure not required
  for this tier.

## 7. Amount Validation

**Decision**: The MCP layer validates money input strings with `Decimal`, rejecting
non-numeric values, zero or negative write amounts, and more than two decimal places before
delegating to banking services.

**Rationale**: MCP tool callers send JSON-compatible values, so accepting string amounts
preserves precision and avoids float parsing. The two-decimal rule is a tool contract
requirement and should fail before any service call can mutate state.

**Alternatives considered**:
- Accept numbers and coerce them to `Decimal` - rejected because JSON numbers can be parsed
  as floating-point values by clients.
- Rely only on existing service validation - rejected because existing services check
  positivity but do not own the MCP-specific decimal-place contract.

## 8. Personal Account Signup

**Decision**: `create_personal_account` mirrors the web signup fields and validation:
name, username, email, phone number, password, and optional initial balance. It does not
create or return an API key.

**Rationale**: The custom user model and account signal already define personal account
creation. API key creation has a separate lifecycle with one-time secret display and user
confirmation, so bundling API key creation into MCP signup would bypass that security model.

**Alternatives considered**:
- Return an API key from signup - rejected because API key generation belongs to the 007
  API-key management feature.
- Require an API key to create a personal account - rejected because signup creates the
  identity that later owns keys.

## 9. Testing Approach

**Decision**: Use pytest + pytest-django with MCP handler tests in `mcp_server/tests/`.
Tests are written first and grouped by user story.

**Rationale**: The project constitution requires test-first development, and the existing
repository already uses pytest as the primary test runner. MCP handlers can be exercised as
plain Python functions with Django test database fixtures.

**Alternatives considered**:
- Manual MCP client testing only - rejected because it is not repeatable enough for money
  and security-sensitive behavior.
- Django's built-in test runner - rejected because the repo standard is pytest.
