# Feature Specification: MCP API Key Authentication

**Feature Branch**: `007-mcp-api-key-auth`  
**Created**: 2026-05-28  
**Status**: Draft  
**Input**: User description: "Add the feature to generate api keys for the account so they can be used as authentication when logging in through mcp servers"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Generate API Key for MCP Access (Priority: P1)

An authenticated account user wants to create a named API key from their account profile so they can connect an MCP client without sharing their account password with that client.

**Why this priority**: Key generation is the foundation for the feature. Without a user-controlled key, there is no safer credential to use for MCP authentication.

**Independent Test**: A signed-in user confirms their identity, creates a named API key, and receives a one-time secret that can be copied for MCP setup.

**Acceptance Scenarios**:

1. **Given** an authenticated account user, **When** they provide the required confirmation and submit a valid key name, **Then** the system creates an API key owned by that user and displays the key secret exactly once.
2. **Given** a newly created API key, **When** the user leaves the confirmation view and later views their API keys, **Then** the full secret is no longer visible or retrievable.
3. **Given** a user who submits an empty or duplicate key name, **When** they attempt to create a key, **Then** the system rejects the request with clear guidance and does not create a key.

---

### User Story 2 - Authenticate to MCP Using an API Key (Priority: P1)

An account user wants an MCP client to authenticate with an API key so the client can perform the same authorised banking actions the user could perform after a normal MCP login.

**Why this priority**: The generated key only delivers value if MCP authentication accepts it and applies the correct user permissions.

**Independent Test**: A valid active API key is used to start an authenticated MCP session, then an action requiring authentication succeeds for the owning user and fails for another user's account.

**Acceptance Scenarios**:

1. **Given** a valid active API key, **When** an MCP client authenticates with it, **Then** the system recognises the owning user and grants an authenticated MCP session for that user.
2. **Given** an authenticated MCP session created with an API key, **When** the client performs a protected operation on the owner's account, **Then** the operation is evaluated with the same permissions as a password-authenticated MCP session for that user.
3. **Given** an API key owned by User A, **When** an MCP client attempts a protected operation on User B's account, **Then** the system rejects the operation and leaves all balances and records unchanged.
4. **Given** an invalid, revoked, expired, or malformed API key, **When** an MCP client attempts to authenticate, **Then** the system rejects the login and does not create an authenticated session.

---

### User Story 3 - Manage Existing API Keys (Priority: P2)

An account user wants to review, identify, and revoke API keys so they can remove access from old devices, compromised clients, or unused MCP integrations.

**Why this priority**: Key management is required for safe long-term use after keys have been issued.

**Independent Test**: A user lists their API keys, revokes one, and confirms that the revoked key can no longer authenticate through MCP while other active keys still work.

**Acceptance Scenarios**:

1. **Given** a user with one or more API keys, **When** they view their account API keys, **Then** they see non-sensitive metadata including key name, status, creation date, last-used date when available, and a non-secret identifier.
2. **Given** an active API key, **When** the owning user revokes it, **Then** the key is marked inactive and can no longer be used for MCP authentication.
3. **Given** a revoked API key, **When** the user views their key list, **Then** the key remains visible as revoked for audit and recognition, but the secret remains hidden.
4. **Given** multiple active API keys, **When** one key is revoked, **Then** other active keys for the same user remain usable.

---

### User Story 4 - Audit API Key Activity (Priority: P3)

An account user or authorised support reviewer wants API key activity to be traceable so suspicious MCP access can be investigated without exposing key secrets.

**Why this priority**: Auditability improves trust and incident response, but the primary user flow can be delivered before expanded review surfaces.

**Independent Test**: Key creation, successful MCP authentication, failed MCP authentication, and revocation are recorded with enough non-sensitive context to understand what happened.

**Acceptance Scenarios**:

1. **Given** a user creates, uses, or revokes an API key, **When** the activity is reviewed, **Then** the event shows the user, key identifier, action, timestamp, and outcome without showing the key secret.
2. **Given** repeated failed MCP authentication attempts with API keys, **When** the activity is reviewed, **Then** the failures are distinguishable from successful authentications and include a safe reason category.

### Edge Cases

- What happens when a user loses a newly generated key secret before saving it?
- How does the system handle an API key that is revoked while an MCP client is already authenticated?
- What happens when an MCP client submits a key with extra whitespace, truncation, or unsupported characters?
- How does the system prevent a user from generating an unbounded number of active keys?
- What happens when a user with a business role uses an API key for manager-only or authoriser-only MCP actions?
- How does the system respond to repeated failed API key authentication attempts?
- What happens when a key has never been used and therefore has no last-used timestamp?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST allow an authenticated account user to generate API keys for their own user identity.
- **FR-002**: API key creation MUST require the user to confirm their identity before the key is issued.
- **FR-003**: Each API key MUST have a user-provided name that helps the owner recognise the MCP client or purpose of the key.
- **FR-004**: The system MUST associate each API key with exactly one user identity and MUST NOT allow a key to be reassigned to another user.
- **FR-005**: The system MUST display the full API key secret only once, immediately after successful key creation.
- **FR-006**: After the one-time display, the system MUST show only non-sensitive key metadata and MUST NOT reveal or recover the full secret.
- **FR-007**: Users MUST be able to view their own API keys with key name, non-secret identifier, status, creation date, last-used date when available, and revocation date when applicable.
- **FR-008**: Users MUST be able to revoke their own active API keys.
- **FR-009**: Revoked API keys MUST be rejected for all future MCP authentication attempts.
- **FR-010**: The system MUST provide a way for users to replace an API key by creating a new key and revoking the old key.
- **FR-011**: MCP authentication MUST accept a valid active API key as a credential for the owning user.
- **FR-012**: A session authenticated with an API key MUST inherit the same MCP permissions and role restrictions as the owning user.
- **FR-013**: API keys MUST NOT grant access to accounts, business roles, pending approvals, or money movement actions that the owning user could not access through normal MCP authentication.
- **FR-014**: API key authentication MUST reject invalid, malformed, revoked, expired, or otherwise inactive keys without creating an authenticated MCP session.
- **FR-015**: Failed API key authentication MUST return a safe error that does not reveal whether a specific key identifier exists.
- **FR-016**: Successful API key authentication MUST update the key's last-used date so users can identify stale keys.
- **FR-017**: The system MUST record non-sensitive audit events for API key creation, successful authentication, failed authentication, and revocation.
- **FR-018**: API key secrets MUST NOT appear in account history views, key list views, MCP responses after authentication, or audit review surfaces.
- **FR-019**: The system MUST enforce a documented maximum number of active API keys per user and clearly explain when the limit is reached.
- **FR-020**: API key management MUST be available to personal users, business managers, and business authorisers for their own login identities.
- **FR-021**: API key authentication MUST NOT change the existing authorisation rules for personal banking actions, business manager submissions, or business authoriser approvals.
- **FR-022**: Existing username-and-password MCP login MUST remain available unless a future policy explicitly disables it.
- **FR-023**: API keys MUST be accepted only for MCP authentication and MUST NOT be accepted as credentials for interactive account sign-in.

### Key Entities

- **Account API Key**: A credential owned by one user identity for MCP authentication; includes a user-visible name, non-secret identifier, status, creation date, last-used date, and revocation date.
- **API Key Secret**: The one-time credential value shown only at creation and used by an MCP client to authenticate.
- **Authenticated MCP Session**: The authenticated context created after a successful login; when created with an API key, it represents the owning user and follows that user's permissions.
- **API Key Audit Event**: A non-sensitive record of key lifecycle and authentication activity, such as creation, successful use, failed use, or revocation.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A user can create, copy, and use a new API key for MCP authentication in under 2 minutes.
- **SC-002**: 100% of protected MCP actions authenticated with a valid active API key are authorised as the owning user and respect that user's existing account and role limits.
- **SC-003**: 100% of invalid, revoked, expired, or malformed API keys are rejected without changing balances, pending approvals, billers, or transaction records.
- **SC-004**: Users can revoke an API key and have future MCP authentication with that key blocked immediately.
- **SC-005**: Key list views never expose full secrets after creation, while still allowing users to identify at least 95% of their keys by name, identifier, status, and last-used information in usability checks.
- **SC-006**: Audit review can distinguish key creation, successful authentication, failed authentication, and revocation events without exposing key secrets.

## Assumptions

- API keys are owned by user identities rather than directly by monetary accounts because MCP permissions are already tied to users and their personal, manager, or authoriser roles.
- Personal users, business managers, and business authorisers can each create keys for their own login identity.
- The API key secret is intended for MCP clients only; it is not a replacement for the user's interactive web password.
- The existing username-and-password MCP login remains available for users who do not create API keys.
- Existing public MCP read and signup behavior remains unchanged unless a later feature revises MCP access policy.
- If a user loses a key secret, they must create a replacement key; the old secret cannot be recovered.
