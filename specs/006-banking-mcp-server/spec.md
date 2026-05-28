# Feature Specification: Personal Banking MCP Server

**Feature Branch**: `006-banking-mcp-server`  
**Created**: 2026-05-25  
**Status**: Draft  
**Input**: User description: "Overhaul the MCP banking server spec: remove all business account tools and only allow logins through API keys."

## Clarifications

### Session 2026-05-28

- Q: Should the MCP server expose business account tools? -> A: No. The MCP surface for this feature is personal banking only. Business account lookup, business transaction history, pending approvals, authoriser actions, and business account signup are out of scope.
- Q: What authentication methods are allowed for MCP login? -> A: API keys only. Username-and-password MCP login is removed from this feature.
- Q: Are account reads public? -> A: No. Personal account details, transactions, and billers are private account data and require an API-key-authenticated MCP session.
- Q: Does personal account signup remain available through MCP? -> A: Yes. Creating a personal account is an open signup operation, not a login operation. After signup, MCP access still requires an API key generated for that user through the account API-key feature.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Authenticate MCP Client With API Key (Priority: P1)

An account user who already created an API key connects an MCP client by presenting that key. The MCP client receives a short-lived authenticated session for the owning user without ever using or storing the user's account password.

**Why this priority**: Every private account lookup and money movement depends on verified identity. API-key-only login is the security boundary for the entire MCP feature.

**Independent Test**: Use a valid active API key to authenticate through MCP, confirm a session token is returned for the key owner, then confirm the same authentication fails for invalid or revoked keys and that no username/password MCP login is available.

**Acceptance Scenarios**:

1. **Given** a valid active API key owned by a user, **When** an MCP client logs in with that key, **Then** it receives a short-lived session token bound to that user.
2. **Given** an invalid, malformed, expired, or revoked API key, **When** an MCP client attempts to log in, **Then** authentication is rejected with a generic failure message and no session is created.
3. **Given** a username and password, **When** an MCP client attempts to use them for MCP login, **Then** no password login path is available and no session is created.
4. **Given** an API-key-authenticated session, **When** the backing API key is revoked before a protected tool is called, **Then** the protected action is rejected and the client must authenticate again with an active key.
5. **Given** a session that has expired through inactivity, **When** a protected tool is called, **Then** the action is rejected before any private data is returned or balance changes are made.

---

### User Story 2 - Query Own Personal Account Information (Priority: P1)

An API-key-authenticated MCP client retrieves the user's personal account summary, transaction history, and saved billers so an AI assistant can answer questions like "What is my balance?", "Show my last transactions", or "Which billers do I have saved?"

**Why this priority**: Read-only account context is the safest and most frequent MCP use case. It must be private to the API key owner.

**Independent Test**: Authenticate with User A's API key and retrieve User A's balance, transactions, and billers. Attempt to retrieve User B's data using the same session and confirm access is denied.

**Acceptance Scenarios**:

1. **Given** a valid API-key-authenticated session, **When** the MCP client requests the account summary, **Then** it receives the authenticated user's name, username, phone number, balance, and account creation date.
2. **Given** a valid session and an account with transactions, **When** the MCP client lists transactions without filters, **Then** it receives the most recent transactions first, including transaction IDs, types, amounts, balance-after values, timestamps, descriptions when present, and counterparties when present.
3. **Given** a valid session and transaction filters for type or date range, **When** the MCP client lists transactions, **Then** only matching transactions for the authenticated user's own account are returned.
4. **Given** a valid session and no transaction history, **When** the MCP client lists transactions, **Then** it receives an empty list with a zero count.
5. **Given** a valid session, **When** the MCP client lists billers, **Then** it receives only billers saved for the authenticated user's personal account.
6. **Given** no valid session token, **When** an MCP client requests account details, transactions, or billers, **Then** the request is rejected.

---

### User Story 3 - Move Personal Funds (Priority: P2)

An API-key-authenticated MCP client deposits funds, withdraws funds, or transfers funds from the authenticated user's personal account to another personal account identified by phone number.

**Why this priority**: Money movement is high value and high risk. It must be constrained to the authenticated user's own account and preserve the no-overdraft rule from core banking.

**Independent Test**: Authenticate with a user's API key, perform a deposit, withdrawal, and transfer with valid amounts, then verify balances and immutable transaction records. Repeat with insufficient funds, invalid amounts, and another user's session to confirm rejection leaves balances unchanged.

**Acceptance Scenarios**:

1. **Given** a valid API-key-authenticated session, **When** the MCP client deposits a positive amount, **Then** the authenticated user's balance increases by exactly that amount and a transaction record is created.
2. **Given** a valid session and sufficient balance, **When** the MCP client withdraws a positive amount, **Then** the authenticated user's balance decreases by exactly that amount and a transaction record is created.
3. **Given** a valid session and a valid recipient phone number, **When** the MCP client transfers a positive amount with an optional description, **Then** the sender balance decreases, the recipient balance increases, and both transaction records include the shared description when provided.
4. **Given** a withdrawal or transfer amount greater than the available balance, **When** the MCP client submits the request, **Then** the operation is rejected and all balances remain unchanged.
5. **Given** a zero, negative, non-numeric, or over-precise amount, **When** the MCP client submits a money movement request, **Then** validation fails before any account is changed.
6. **Given** a recipient phone number that does not identify a registered personal account, **When** the MCP client submits a transfer, **Then** the transfer is rejected and no balances change.
7. **Given** the authenticated user's own phone number as the transfer recipient, **When** the MCP client submits a transfer, **Then** the transfer is rejected.

---

### User Story 4 - Manage and Pay Personal Billers (Priority: P2)

An API-key-authenticated MCP client adds saved billers from the fixed billing categories, lists saved billers, and pays bills from the authenticated user's personal account.

**Why this priority**: Bill payment is a common delegated banking task and depends on the fixed-category billing model.

**Independent Test**: Authenticate with a user's API key, add a valid biller category and reference, list it, pay it with sufficient funds, and confirm the balance and transaction history update correctly. Repeat with duplicate billers, invalid categories, wrong biller ownership, and insufficient funds.

**Acceptance Scenarios**:

1. **Given** a valid API-key-authenticated session, **When** the MCP client adds a biller using one of the five predefined categories and a mandatory reference, **Then** the biller is saved to the authenticated user's personal account.
2. **Given** a saved biller, **When** the MCP client lists billers, **Then** the biller appears with category, category display name, reference, and creation date.
3. **Given** a duplicate category and reference for the same account, **When** the MCP client attempts to add the biller again, **Then** the request is rejected and no duplicate is saved.
4. **Given** an invalid category or blank reference, **When** the MCP client attempts to add a biller, **Then** validation fails and no biller is saved.
5. **Given** a valid session, saved biller, sufficient balance, and positive payment amount, **When** the MCP client pays the bill, **Then** the user's balance decreases and a bill payment transaction is recorded.
6. **Given** a biller that does not belong to the authenticated user's account, **When** the MCP client attempts to pay it, **Then** the payment is rejected without revealing another user's biller details.

---

### User Story 5 - Open a Personal Account Through MCP (Priority: P3)

A new customer can create a personal account through MCP by providing the same identity and contact details used by the web signup flow, including an optional initial balance for demo or setup purposes.

**Why this priority**: Signup is useful for demo and onboarding flows, but existing users with API keys receive the primary MCP value.

**Independent Test**: Create a personal account with unique username, email, and phone number, confirm the account exists with the requested starting balance, then confirm duplicate identity fields and invalid initial balances are rejected.

**Acceptance Scenarios**:

1. **Given** a new customer with unique signup details, **When** the MCP client creates a personal account, **Then** the account is created with the submitted name, username, email, phone number, password, and starting balance.
2. **Given** the optional initial balance is omitted or explicitly zero, **When** the account is created, **Then** the account starts with a zero balance.
3. **Given** the optional initial balance is positive and valid, **When** the account is created, **Then** the account starts with that balance.
4. **Given** a username, email, or phone number already used by another account, **When** the MCP client attempts signup, **Then** signup is rejected with a clear error and no duplicate account is created.
5. **Given** an invalid phone number, weak password, negative initial balance, or non-numeric initial balance, **When** the MCP client attempts signup, **Then** signup is rejected with a clear validation error.
6. **Given** a newly created personal account, **When** the user wants to use authenticated MCP tools, **Then** they must first create an API key for that account through the account API-key feature.

---

### Edge Cases

- What happens when an API key is revoked while an MCP session created by that key is still active?
- What happens when an MCP client attempts username-and-password login after API-key-only login is enforced?
- What happens when a protected personal account tool is called with no session token, an expired token, or a token created from a revoked API key?
- What happens when a client tries to target another user's account by passing another username, account ID, phone number, biller ID, or transaction filter?
- What happens when a model requests a business account tool such as business lookup, business transaction history, pending approvals, approval, rejection, or business signup?
- What happens when a deposit, withdrawal, transfer, or bill payment amount is zero, negative, non-numeric, or has more than two decimal places?
- What happens when a withdrawal, transfer, or bill payment would reduce the authenticated user's balance below zero?
- What happens when a transfer recipient does not exist or matches the sender's own phone number?
- What happens when a transfer description exceeds the allowed length?
- What happens when an add-biller request uses an unsupported category, omits the reference, or duplicates an existing category and reference for the same account?
- What happens when personal signup submits duplicate username, email, or phone number values?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The MCP server MUST expose a `login_with_api_key` tool that accepts an API key and, on success, returns a short-lived session token for the owning user.
- **FR-002**: The MCP server MUST reject invalid, malformed, expired, or revoked API keys with a generic authentication error and MUST NOT create a session.
- **FR-003**: The MCP server MUST NOT expose or support username-and-password MCP login.
- **FR-004**: Session tokens issued by API-key login MUST expire after a defined period of inactivity.
- **FR-005**: Protected tool calls using API-key-backed sessions MUST confirm the backing API key remains active before returning private data or performing any write.
- **FR-006**: All tools that read or modify an existing personal account MUST require a valid API-key-authenticated session token.
- **FR-007**: Protected personal account tools MUST operate only on the personal account owned by the authenticated session user.
- **FR-008**: The MCP server MUST NOT expose business account tools, including business account lookup, business transaction history, pending transaction listing, approval, rejection, or business account creation.
- **FR-009**: The MCP server MUST expose a protected `get_account` tool that returns the authenticated user's personal account details, including username, name, phone number, balance, and account creation date.
- **FR-010**: The MCP server MUST expose a protected `list_transactions` tool that returns the authenticated user's personal transactions ordered newest first, with optional filters for transaction type and date range.
- **FR-011**: Transaction results MUST include transaction ID, type, amount, balance after the transaction, timestamp, description when present, and counterparty identity when present.
- **FR-012**: The MCP server MUST expose a protected `deposit_funds` tool that deposits a positive amount into the authenticated user's personal account and records an immutable transaction.
- **FR-013**: The MCP server MUST expose a protected `withdraw_funds` tool that withdraws a positive amount from the authenticated user's personal account and records an immutable transaction.
- **FR-014**: The MCP server MUST reject any withdrawal that would reduce the authenticated user's balance below zero.
- **FR-015**: The MCP server MUST expose a protected `transfer_funds` tool that transfers a positive amount from the authenticated user's personal account to another personal account identified by phone number.
- **FR-016**: The MCP server MUST reject transfers to non-existent recipients and transfers to the sender's own account.
- **FR-017**: The MCP server MUST reject any transfer that would reduce the sender's balance below zero.
- **FR-018**: Transfer descriptions MUST be optional, limited to the existing transfer description length, and recorded on both sender and recipient transaction records when provided.
- **FR-019**: The MCP server MUST expose a protected `list_billers` tool that returns only the authenticated user's saved personal billers.
- **FR-020**: The MCP server MUST expose a protected `add_biller` tool that accepts one of the five predefined billing categories and a mandatory reference.
- **FR-021**: The valid biller categories MUST be Electricity, Water & Utilities, Internet & Broadband, Telecommunications, and Town Council / Maintenance.
- **FR-022**: The MCP server MUST reject add-biller requests with unsupported categories, blank references, or duplicate category-and-reference pairs for the authenticated user's account.
- **FR-023**: The MCP server MUST expose a protected `pay_bill` tool that pays one of the authenticated user's saved billers with a positive amount and records an immutable bill payment transaction.
- **FR-024**: The MCP server MUST reject bill payments for billers that do not belong to the authenticated user's account.
- **FR-025**: The MCP server MUST reject bill payments that would reduce the authenticated user's balance below zero.
- **FR-026**: All money amounts accepted by MCP tools MUST be exact decimal values with no more than two decimal places.
- **FR-027**: All deposit, withdrawal, transfer, and bill payment requests MUST reject zero, negative, non-numeric, and over-precise amounts before changing account state.
- **FR-028**: Any failed validation, authentication, authorisation, insufficient-funds, or not-found result MUST leave balances, billers, and transactions unchanged.
- **FR-029**: All tool failures MUST return structured error responses with enough context for an MCP client to explain the failure safely.
- **FR-030**: The MCP server MUST expose an open `create_personal_account` tool that accepts name, username, email, phone number, password, and optional initial balance.
- **FR-031**: Personal account creation MUST enforce username, email, and phone number uniqueness, phone-number format rules, and password-strength rules consistent with the account signup feature.
- **FR-032**: Personal account creation MUST default the starting balance to zero when the initial balance is omitted or explicitly zero.
- **FR-033**: Personal account creation MUST reject negative, non-numeric, or over-precise initial balances and MUST NOT create a partial account on failure.
- **FR-034**: Personal account creation MUST NOT create or return an API key; API-key lifecycle and one-time key display remain governed by the API-key authentication feature.

### Key Entities

- **User**: A person who owns a personal banking account and may create API keys for MCP authentication. Identified by a unique username, email address, and phone number.
- **Personal Account**: The authenticated user's monetary account. Holds a balance, belongs to exactly one user, and must never become negative.
- **Account API Key**: A user-owned MCP credential that can create an authenticated MCP session without sharing the user's password.
- **Authenticated MCP Session**: A short-lived session created only through API-key login. It represents one user and authorises tools only for that user's personal account.
- **Transaction**: An immutable record of a personal account money movement, including transaction ID, type, amount, timestamp, balance after the transaction, optional description, and optional counterparty.
- **Biller**: A saved payee reference belonging to one personal account. It has one of the five fixed billing categories and a mandatory reference unique within the same account and category.
- **Bill Payment**: A completed payment from a personal account to one of that account's saved billers, represented in transaction history as a bill payment transaction.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of MCP sessions are created through valid active API keys; username-and-password MCP login creates zero sessions.
- **SC-002**: 100% of invalid, malformed, expired, or revoked API keys are rejected without returning private account data or changing balances, billers, or transactions.
- **SC-003**: 100% of protected account reads and writes are scoped to the authenticated user's own personal account.
- **SC-004**: The MCP tool list contains no business account tools, and business account operations are unavailable through this feature.
- **SC-005**: All 10 supported personal MCP tools (`create_personal_account`, `login_with_api_key`, `get_account`, `list_transactions`, `list_billers`, `deposit_funds`, `withdraw_funds`, `transfer_funds`, `add_biller`, and `pay_bill`) return correct results for valid inputs.
- **SC-006**: 100% of failed money movement and bill payment attempts leave balances and transaction history unchanged.
- **SC-007**: 100% of successful money movement and bill payment actions create immutable transaction records with transaction IDs and accurate balance-after values.
- **SC-008**: Transaction history returned through MCP includes counterparty and description data for all applicable transfers.
- **SC-009**: Users can authenticate with an API key and complete a common read-only query, such as checking balance or listing recent transactions, in under 2 seconds under normal operating conditions.

## Assumptions

- API key creation, revocation, one-time secret display, and audit activity are defined by `specs/007-mcp-api-key-auth/`; this MCP spec consumes that authentication capability rather than redefining the key management UI.
- Personal banking behavior follows the core banking requirements: one personal account per user, exact monetary values, no overdrafts, phone-number recipient lookup, and immutable transaction history.
- Transfer descriptions follow the UX enhancement requirement: optional plain text with the existing maximum length and visible in both parties' transaction history.
- Billers follow the billing system requirements: five fixed categories, mandatory reference, and uniqueness per personal account plus category.
- The personal account signup tool is unauthenticated because it creates a new account; authenticated access to existing account data still requires an API key.
- Business accounts, manager submissions, authoriser approvals, pending transactions, and business account creation remain outside this MCP feature.
- API keys are accepted only for MCP authentication and are not accepted for interactive web sign-in.
- The MCP server targets local or trusted-client banking assistant integrations and does not integrate with external banks, card networks, or payment processors.
