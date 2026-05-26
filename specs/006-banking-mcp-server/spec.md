# Feature Specification: Banking MCP Server

**Feature Branch**: `006-banking-mcp-server`  
**Created**: 2026-05-25  
**Status**: Draft  
**Input**: User description: "An MCP server for models to use tools for our banking app. Come up with the tools that models can use"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Query Account Information (Priority: P1)

An AI model needs to look up the current balance and account details for a user or business account so it can answer questions like "What is my balance?" or "Show me my account summary."

**Why this priority**: Read-only account information is the most fundamental capability — every other tool depends on knowing account state. It delivers immediate value with no side effects.

**Independent Test**: A model can be given a username and asked "What is the account balance?" — the tool returns the correct balance and account details without any other tools being present.

**Acceptance Scenarios**:

1. **Given** a valid personal account username, **When** a model calls the get-account tool, **Then** it receives the account holder name, balance, and account creation date.
2. **Given** a valid business UEN or company name, **When** a model calls the get-business-account tool, **Then** it receives the company name, UEN, address, balance, and manager details.
3. **Given** an invalid or non-existent username, **When** a model calls the get-account tool, **Then** it receives a clear error indicating the account was not found.

---

### User Story 2 - Browse Transaction History (Priority: P1)

An AI model needs to retrieve and filter a user's or business's transaction history so it can answer questions like "Show me my last 10 transactions" or "What did I spend on bill payments this month?"

**Why this priority**: Transaction history is the second most critical read capability — users frequently ask AI assistants to summarise or search their financial activity.

**Independent Test**: A model can retrieve and filter transactions for a personal or business account, returning a paginated list with type, amount, counterparty, and timestamp, without any write tools present.

**Acceptance Scenarios**:

1. **Given** a valid account, **When** a model calls the list-transactions tool with no filters, **Then** it receives the 20 most recent transactions ordered by newest first.
2. **Given** a valid account and a filter for transaction type (e.g., BILL_PAYMENT), **When** the tool is called, **Then** only transactions matching that type are returned.
3. **Given** a valid account and a date range filter, **When** the tool is called, **Then** only transactions within that range are returned.
4. **Given** an account with no transactions, **When** the tool is called, **Then** it returns an empty list with a clear indication that no transactions exist.

---

### User Story 3 - Execute Personal Account Transfers (Priority: P2)

An AI model needs to initiate a transfer of funds from one personal account to another so it can fulfil requests like "Transfer $50 to John."

**Why this priority**: Transfers are the most common write action users delegate to AI assistants. Placing it at P2 ensures read capabilities are solid first.

**Independent Test**: A model can call the transfer tool with a source username, destination username, and amount, and the balances of both accounts update correctly with a corresponding transaction record created.

**Acceptance Scenarios**:

1. **Given** two valid accounts with sufficient funds, **When** a model calls the transfer tool, **Then** the sender's balance decreases and the recipient's balance increases by the specified amount, and a TRANSFER_OUT and TRANSFER_IN transaction are recorded.
2. **Given** an account with insufficient balance, **When** a model calls the transfer tool, **Then** no balance change occurs and an error describing the shortfall is returned.
3. **Given** an invalid recipient username, **When** a model calls the transfer tool, **Then** no balance change occurs and a clear not-found error is returned.
4. **Given** a transfer amount of zero or a negative number, **When** the tool is called, **Then** a validation error is returned.

---

### User Story 4 - Deposit and Withdraw Funds (Priority: P2)

An AI model needs to deposit funds into or withdraw funds from a personal account to fulfil requests like "Deposit $200 into my account" or "Withdraw $100."

**Why this priority**: Deposits and withdrawals are common self-service operations that models should be able to handle on behalf of users.

**Independent Test**: A model can call the deposit tool to increase a balance and the withdrawal tool to decrease it, with transaction records created for each operation.

**Acceptance Scenarios**:

1. **Given** a valid account, **When** a model calls the deposit tool with a positive amount, **Then** the balance increases by that amount and a DEPOSIT transaction is recorded.
2. **Given** a valid account with sufficient funds, **When** a model calls the withdrawal tool, **Then** the balance decreases by that amount and a WITHDRAWAL transaction is recorded.
3. **Given** a withdrawal amount exceeding the current balance, **When** the tool is called, **Then** the operation is rejected and the balance remains unchanged.

---

### User Story 5 - Manage and Pay Bills (Priority: P2)

An AI model needs to retrieve saved billers and submit bill payments on behalf of a personal account user, supporting requests like "Pay my electricity bill" or "List my billers."

**Why this priority**: Bill payments are a scheduled, recurring need that is well-suited to AI delegation.

**Independent Test**: A model can list all billers for an account, and then call the pay-bill tool to execute a bill payment, resulting in a BILL_PAYMENT transaction and an updated balance.

**Acceptance Scenarios**:

1. **Given** a valid account, **When** a model calls the list-billers tool, **Then** it receives all saved billers with their category, reference, and creation date.
2. **Given** a valid account and a known biller reference, **When** a model calls the pay-bill tool with an amount, **Then** the balance decreases and a BILL_PAYMENT transaction is recorded.
3. **Given** a biller reference that does not belong to the account, **When** the pay-bill tool is called, **Then** no payment is made and an error is returned.

---

### User Story 6 - Manage Business Account Pending Transactions (Priority: P3)

An AI model acting as an authoriser needs to list, approve, or reject pending business transactions so it can fulfil requests like "Show pending approvals" or "Approve the $5,000 transfer."

**Why this priority**: Business approval workflows are critical but serve a narrower audience (authorisers and managers) than personal account operations.

**Independent Test**: A model can list pending transactions for a business account, then approve or reject one, with the business account balance updating on approval and the pending transaction status changing accordingly.

**Acceptance Scenarios**:

1. **Given** a business account with pending transactions, **When** a model calls the list-pending-transactions tool, **Then** it receives all PENDING transactions with type, amount, counterparty, and creation date.
2. **Given** a PENDING transaction ID, **When** a model calls the approve-transaction tool, **Then** the transaction status changes to APPROVED, the business balance updates, and a BusinessTransaction record is created.
3. **Given** a PENDING transaction ID, **When** a model calls the reject-transaction tool with an optional reason, **Then** the transaction status changes to REJECTED and the balance remains unchanged.
4. **Given** a transaction that is already APPROVED, **When** a model calls approve-transaction, **Then** an error is returned indicating the transaction is no longer pending.

---

### User Story 7 - User Login and Session Management (Priority: P1)

A user must log in with their username and password before the MCP server will execute any write operation on their behalf. The model calls the login tool once per session; subsequent write tool calls use the returned session token instead of re-prompting for credentials.

**Why this priority**: Without verified identity, any connected model could operate on any account. This is a hard prerequisite for safely deploying write tools.

**Independent Test**: A model calls `login` with valid credentials and receives a session token. A subsequent `transfer_funds` call using that token succeeds. The same transfer call without a token, or with an expired token, is rejected before any balance changes.

**Acceptance Scenarios**:

1. **Given** a valid username and correct password, **When** a model calls `login`, **Then** it receives a short-lived session token tied to that user.
2. **Given** a valid username and incorrect password, **When** a model calls `login`, **Then** it receives an authentication error and no token is issued.
3. **Given** a non-existent username, **When** a model calls `login`, **Then** it receives an authentication error.
4. **Given** a write tool call with a valid, unexpired session token, **When** the token's user matches the account being operated on, **Then** the operation executes normally.
5. **Given** a write tool call with an expired or invalid session token, **When** the server receives the request, **Then** it returns a session-expired error and does not execute the operation.
6. **Given** a write tool call where the token belongs to User A but the target account belongs to User B, **When** the server validates the request, **Then** it returns an authorisation error.
7. **Given** a valid session token for the assigned authoriser, **When** `approve_transaction` or `reject_transaction` is called, **Then** the operation executes. For any other user's token, an authorisation error is returned.
8. **Given** a read-only tool call (`get_account`, `list_transactions`, etc.), **When** it is made without a session token, **Then** it executes normally — read tools do not require authentication.

---

### Edge Cases

- What happens when a model calls a write tool (transfer, deposit, withdrawal, bill payment) with an amount that has more than two decimal places?
- How does the server handle concurrent calls that could cause a race condition on the same account balance?
- What happens when a model provides a negative transfer amount disguised as a positive one?
- How does the server respond when the banking app's database is unreachable?
- What happens when a business account has no assigned authoriser and an approve/reject action is attempted?
- What happens when a write tool is called without a `session_token` parameter?
- What happens if a model reuses an expired token multiple times — does the server issue a distinct "please re-login" message?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The MCP server MUST expose a `get_account` tool that returns personal account details (holder name, balance, creation date) given a username.
- **FR-002**: The MCP server MUST expose a `get_business_account` tool that returns business account details (company name, UEN, address, balance, manager) given a UEN or company name.
- **FR-003**: The MCP server MUST expose a `list_transactions` tool that returns paginated transactions for a personal account, with optional filters for transaction type and date range.
- **FR-004**: The MCP server MUST expose a `list_business_transactions` tool that returns paginated transactions for a business account, with optional filters for transaction type and date range.
- **FR-005**: The MCP server MUST expose a `transfer_funds` tool that moves a specified amount from one personal account to another, recording TRANSFER_OUT and TRANSFER_IN transactions.
- **FR-006**: The MCP server MUST expose a `deposit_funds` tool that adds a specified amount to a personal account balance and records a DEPOSIT transaction.
- **FR-007**: The MCP server MUST expose a `withdraw_funds` tool that deducts a specified amount from a personal account balance and records a WITHDRAWAL transaction.
- **FR-008**: The MCP server MUST expose a `list_billers` tool that returns all saved billers for a personal account.
- **FR-009**: The MCP server MUST expose a `pay_bill` tool that executes a bill payment from a personal account to a named biller, recording a BILL_PAYMENT transaction.
- **FR-010**: The MCP server MUST expose a `list_pending_transactions` tool that returns all PENDING transactions for a business account.
- **FR-011**: The MCP server MUST expose an `approve_transaction` tool that changes a PENDING business transaction to APPROVED and executes the corresponding balance change.
- **FR-012**: The MCP server MUST expose a `reject_transaction` tool that changes a PENDING business transaction to REJECTED without affecting the balance.
- **FR-013**: All write tools (transfer, deposit, withdrawal, bill payment, approve, reject) MUST validate that amounts are positive and have at most two decimal places before executing.
- **FR-014**: All tools MUST return structured error responses with a human-readable message when an operation fails (account not found, insufficient funds, invalid input, etc.).
- **FR-015**: The MCP server MUST operate as a stateless request handler — it does not store sessions or user state between tool calls.
- **FR-016**: The MCP server MUST expose a `login` tool that accepts a username and password; on success it returns a short-lived session token, on failure it returns an authentication error with no token.
- **FR-017**: All write tools MUST accept a `session_token` parameter; the server MUST validate the token before executing the operation and reject expired or invalid tokens.
- **FR-018**: All write tools MUST verify that the authenticated user (identified by the session token) is authorised to operate on the target account — users may only act on their own accounts.
- **FR-019**: The `approve_transaction` and `reject_transaction` tools MUST verify that the session token belongs to the assigned authoriser for the relevant business account before executing.
- **FR-020**: Read-only tools (`get_account`, `get_business_account`, `list_transactions`, `list_business_transactions`, `list_billers`, `list_pending_transactions`) do NOT require a session token.
- **FR-022**: The `create_personal_account` and `create_business_account` tools do NOT require a session token — they are open signup operations available to unauthenticated callers.
- **FR-023**: The MCP server MUST expose a `create_personal_account` tool that accepts a username, password, and an optional initial deposit (minimum 0.00, defaults to 0); on success it returns the created account details.
- **FR-024**: The MCP server MUST expose a `create_business_account` tool that accepts a business name, UEN, address (street, city, postal code), and an optional initial deposit (minimum 7,000); on success it atomically creates the business account, one account manager user, and one authoriser user (credentials auto-generated from business name, matching the web app pattern), and returns all three sets of details including the generated credentials. The initial deposit MUST be recorded as a deposit transaction.
- **FR-025**: `create_business_account` MUST reject creation if the initial deposit is below 7,000, returning a clear validation error. The business account balance MUST remain ≥ 7,000 at all times (consistent with FR from 003-business-account).
- **FR-026**: `create_business_account` MUST reject creation if the submitted UEN already exists, returning a clear duplication error.
- **FR-027**: The MCP server MUST expose an `add_biller` tool that accepts a `session_token`, `category` (one of: Electricity, Water & Utilities, Internet & Broadband, Telecommunications, Town Council / Maintenance), and `reference` (mandatory, unique per account + category); on success it returns the saved biller details.
- **FR-028**: `add_biller` MUST reject the request if the category is not one of the five predefined values, returning a validation error.
- **FR-029**: `add_biller` MUST reject the request if a biller with the same category and reference already exists for that account, returning a clear duplication error.
- **FR-021**: Session tokens MUST expire after a defined period of inactivity; the server MUST return a clear session-expired error when a stale token is used.

### Key Entities

- **PersonalAccount**: A user's monetary account; has one balance, one owner, and a history of transactions.
- **BusinessAccount**: A company's monetary account; has a balance, a UEN, an address, an account manager, an authoriser, and a history of transactions and pending transactions.
- **Transaction**: An immutable record of a balance-changing event on a personal account (deposit, withdrawal, transfer, bill payment).
- **BusinessTransaction**: An immutable record of an executed or rejected event on a business account.
- **PendingTransaction**: A queued outgoing action on a business account awaiting authoriser approval or rejection.
- **Biller**: A saved payee reference linked to a personal account for recurring bill payments. Has a `category` (one of 5 predefined values) and a `reference` (unique per account + category). No free-text name field.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Each tool call returns a response in under 2 seconds under normal operating conditions.
- **SC-002**: All 16 tools (12 read/write originals + `login` + `create_personal_account`, `create_business_account`, `add_biller`) are callable and return correct results for valid inputs 100% of the time in the test suite.
- **SC-003**: All write operations that fail validation leave the account balance unchanged — verified by before/after balance checks in tests.
- **SC-004**: An AI model with access only to these tools can answer at least 90% of common banking queries (balance lookup, transaction history, transfer, bill payment) without requiring direct database or UI access.
- **SC-005**: All tool error responses include enough context for the calling model to relay a meaningful message to the user without additional lookups.

## Clarifications

### Session 2026-05-26

- Q: Who is allowed to call `create_personal_account` and `create_business_account`? → A: Unauthenticated — no session token required (open signup)
- Q: What should the starting balance be when a new personal or business account is created? → A: Caller provides an optional initial deposit; personal account minimum is 0.00 (defaults to 0), business account minimum is 7,000 (inclusive, per 003-business-account spec)
- Q: What fields are required when adding a biller? → A: `category` (one of 5 predefined values: Electricity, Water & Utilities, Internet & Broadband, Telecommunications, Town Council / Maintenance) and `reference` (mandatory, unique per account + category); no free-text name field (per 004-billing-system spec)
- Q: Should `add_biller` require a session token? → A: Yes — consistent with all other write tools
- Q: Should `create_business_account` auto-create manager and authoriser users and return their credentials? → A: Yes — mirrors the web app; creates manager + authoriser atomically and returns generated credentials in the response

## Assumptions

- The MCP server communicates directly with the banking app's existing data layer (same database); it does not call the app's HTTP endpoints.
- Session tokens are short-lived; the specific expiry duration is a configuration detail left to implementation.
- The `login` tool validates credentials against the banking app's existing user store — no separate user database is introduced.
- Token storage (in-memory, database, cache) is an implementation detail; the spec only requires that tokens expire and are validated on every write call.
- The server handles one request at a time per tool call; concurrent safety is delegated to the database's existing transaction mechanisms.
- Mobile or multi-platform MCP client support is out of scope; the server targets desktop and server-based AI agent environments.
- The `transfer_funds` tool only supports transfers between two personal accounts; business-to-personal and business-to-business transfers follow the pending transaction approval workflow.
