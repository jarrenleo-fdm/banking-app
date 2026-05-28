# Research: MCP API Key Authentication

## 1. API key ownership model

**Decision**: API keys are owned by `accounts.CustomUser`, not by `banking.Account` or
`banking.BusinessAccount`.

**Rationale**: MCP authorisation already starts from a user identity. Personal users,
business managers, and business authorisers are all `CustomUser` rows, and business
permissions are derived from `AccountManagerProfile` and `Authoriser`. User-owned keys
therefore inherit the existing role model without introducing an account-level credential
that could blur personal and business access.

**Alternatives considered**:
- Personal-account-owned keys — would not map cleanly to business manager or authoriser
  users, whose business authority is separate from their auto-created personal account.
- Business-account-owned keys — would require a separate authorisation model to decide
  whether the key acts as manager or authoriser.

---

## 2. Secret storage and one-time reveal

**Decision**: Generate a high-entropy raw secret, show it only once, and store only a
hash plus non-secret metadata.

**Rationale**: API keys are credentials. Storing raw secrets would violate the
constitution's security and audit principles. A one-time reveal lets users configure an
MCP client while ensuring later database reads, admin screens, logs, or templates cannot
recover the secret.

**Alternatives considered**:
- Re-displayable API keys — convenient but unsafe because database compromise would expose
  every active credential.
- Encrypted reversible secrets — still recoverable by the application and unnecessary
  because verification only needs comparison, not decryption.

---

## 3. Key identifier and lookup

**Decision**: Use a non-secret public identifier for display and lookup, separate from the
secret material used for verification.

**Rationale**: Users need to recognise keys in list and audit views. The MCP server also
needs an efficient way to find a candidate key before comparing a submitted secret. The
identifier is safe to display because it cannot authenticate by itself.

**Alternatives considered**:
- Lookup by full secret hash across all keys — simpler fields, but less ergonomic for
  display and rotation.
- Username plus secret only — requires users to supply two values and duplicates the
  existing username/password login shape.

---

## 4. MCP authentication contract

**Decision**: Add a separate `login_with_api_key(api_key)` MCP tool that returns the same
short-lived `session_token` shape as the existing `login(username, password)` tool.

**Rationale**: A separate tool avoids ambiguous optional parameters on `login`, preserves
backward compatibility for existing MCP clients, and keeps all protected write tools
unchanged because they already accept `session_token`.

**Alternatives considered**:
- Extend `login` with optional API key fields — would make validation and client schemas
  ambiguous.
- Pass API keys directly to every protected write tool — increases secret exposure and
  requires changing every tool contract.

---

## 5. Revocation semantics

**Decision**: Revocation blocks future API-key login immediately and also blocks future
protected actions for sessions that were created by that API key.

**Rationale**: Users revoke keys because access should stop. If a session token issued
from a revoked key could continue until idle expiry, the user-facing security promise
would be weaker. Re-checking the key status during protected token validation keeps
revocation meaningful even while the MCP server is running.

**Alternatives considered**:
- Let existing sessions expire naturally — simpler, but surprising and less safe for a
  compromised key.
- Delete all MCP sessions on any revocation — would unnecessarily disrupt unrelated keys
  and password-authenticated sessions.

---

## 6. Active key limit

**Decision**: Limit each user to 5 active API keys.

**Rationale**: The feature is for a small prototype and users should usually need only a
few MCP clients. A low documented limit reduces credential sprawl while still supporting
multiple devices or tools.

**Alternatives considered**:
- Unlimited keys — makes stale credentials more likely.
- One active key per user — makes rotation awkward because users could not create a new key
  before revoking the old one.

---

## 7. Identity confirmation

**Decision**: Require the current account password when creating an API key.

**Rationale**: This confirms a fresh user action before issuing a long-lived credential and
works within the current app, which does not yet provide MFA. It also applies equally to
personal users, managers, and authorisers.

**Alternatives considered**:
- No confirmation beyond being signed in — too weak for a credential creation action.
- MFA confirmation — preferred for production but not yet available in the prototype.

---

## 8. Audit events

**Decision**: Store API key lifecycle and authentication audit events in a dedicated
accounts-owned audit model.

**Rationale**: API key events are security events, not banking transactions. A dedicated
model keeps transaction history immutable and money-focused while still making key
creation, use, failures, and revocations reconstructable.

**Alternatives considered**:
- Application logs only — useful operationally but harder to query in tests and less
  suitable for user/account-specific audit review.
- Reusing `Transaction` or `BusinessTransaction` — incorrect domain boundary because API
  key events do not move money.

---

## 9. Failed authentication attempts

**Decision**: Failed API key authentication returns a generic error and records a
non-sensitive audit event. Durable rate limiting is deferred to the Production Migration
TODO.

**Rationale**: Generic errors avoid key enumeration. Audit events provide traceability in
the prototype without introducing new infrastructure. Production should add durable
rate-limiting storage so repeated attempts can be slowed across server restarts and
multiple MCP processes.

**Alternatives considered**:
- Detailed failure messages — easier debugging, but leaks whether an identifier exists.
- In-memory lockout only — weak across restarts and multi-process use; acceptable only as
  a supplemental defense, not the primary production control.
