# Feature Specification: Business Account Registration

**Feature Branch**: `003-business-account`  
**Created**: 2026-05-21  
**Status**: Draft  
**Input**: User description: "Add the option to create a business account"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Create Business Account (Priority: P1)

A bank staff member (or demo operator) visits `/business/create` and fills in the business name, UEN, and address. On submit, the system runs mock SQL that creates: a business account, an account manager user, and an authoriser user. The generated credentials for both users are displayed once on the confirmation screen.

**Why this priority**: This is the entry point for the entire feature. Without a created business account (and its associated users), the manager and authoriser flows cannot be tested.

**Independent Test**: Visit `/business/create`, fill in valid details, submit, and confirm that credentials for both the account manager and authoriser are shown, and that both users can subsequently log in.

**Acceptance Scenarios**:

1. **Given** a visitor is on `/business/create`, **When** they submit a valid business name, UEN, and address, **Then** the system creates a business account, an account manager user, and an authoriser user — and displays the generated credentials for both on a confirmation screen.
2. **Given** a visitor submits the form with a blank business name, UEN, or any address field, **When** the form is submitted, **Then** validation errors are shown per field and no account is created.
3. **Given** a visitor submits a UEN that already exists, **When** the form is submitted, **Then** a clear duplication error is shown and no account is created.

---

### User Story 2 - Account Manager Submits a Transaction (Priority: P1)

The account manager logs into their generated account and navigates to the business account view. They can submit any transaction type on behalf of the business account. Deposits execute immediately; outgoing transactions (withdrawal, transfer, bill payment) enter a pending state awaiting authoriser approval.

**Why this priority**: This is the primary operational flow — without it the approval queue has nothing to act on.

**Independent Test**: Log in as the account manager, submit a withdrawal for the business account, confirm it appears in the pending queue and the business account balance has not changed.

**Acceptance Scenarios**:

1. **Given** an account manager is logged in, **When** they submit a deposit for the business account, **Then** the deposit executes immediately and the business account balance increases.
2. **Given** an account manager is logged in, **When** they submit a withdrawal, transfer, or bill payment for the business account, **Then** the transaction enters a "Pending" state, the balance does not change, and the transaction appears in the pending queue.
3. **Given** an account manager submits an outgoing transaction with insufficient balance, **When** the form is submitted, **Then** a clear error is shown and no pending transaction is created.

---

### User Story 3 - Authoriser Approves or Rejects a Pending Transaction (Priority: P1)

The authoriser logs into their generated account. If pending transactions exist for their business account, a visible link to the pending queue appears on their dashboard. They can approve or reject each transaction individually.

**Why this priority**: Without this flow, outgoing transactions are permanently blocked — the approval queue is the core control mechanism.

**Independent Test**: Log in as the authoriser after the account manager has submitted an outgoing transaction. Confirm the pending queue link is visible, approve the transaction, and verify the business account balance decreases and the transaction no longer appears as pending.

**Acceptance Scenarios**:

1. **Given** the authoriser is logged in and pending transactions exist, **When** they view their dashboard, **Then** a visible link/button to the pending transactions queue is shown.
2. **Given** the authoriser is on the pending queue, **When** they approve a transaction, **Then** the transaction executes immediately, the business account balance updates, and the transaction is removed from the pending queue.
3. **Given** the authoriser is on the pending queue, **When** they reject a transaction, **Then** the transaction is cancelled, removed from the pending queue, and recorded in the business account transaction history with status "Rejected".
4. **Given** the authoriser is logged in and no pending transactions exist, **When** they view their dashboard, **Then** the pending queue link is NOT shown.

---

### Edge Cases

- What happens when a UEN is submitted that already exists? → Duplicate error shown; no account created.
- What happens when any required field (business name, UEN, address) is blank or whitespace only? → Field-level validation error; form does not submit.
- What happens if the account manager submits an outgoing transaction when the business account has insufficient funds? → Error shown; no pending transaction created.
- What happens if the authoriser tries to act on a transaction that was already approved or rejected? → No-op; transaction state is unchanged (already resolved).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST provide a public page at `/business/create` (no login required) with a form accepting: business name, UEN, and address (street, city, postal code).
- **FR-002**: The system MUST validate that business name, UEN, street, city, and postal code are non-empty and non-whitespace before creating any account.
- **FR-003**: UENs MUST be unique. The system MUST reject creation with a clear validation error if the submitted UEN already exists. Any non-empty alphanumeric string is accepted as a valid UEN; no format pattern is enforced.
- **FR-004**: On successful form submission, the system MUST execute mock SQL that creates: (1) a `BusinessAccount` entity, (2) an account manager `User` linked 1:1 to the business account, (3) an authoriser `User` linked 1:1 to the business account. Credentials for both users MUST be auto-generated from the business name and displayed once on the confirmation screen.
- **FR-005**: The account manager's dashboard MUST show the business account details (name, balance, transaction history) and provide access to the transaction submission form for that business account.
- **FR-006**: The account manager MUST be able to submit all transaction types (deposit, withdrawal, transfer, bill payment) for the business account.
- **FR-007**: Deposits submitted by the account manager MUST execute immediately and update the business account balance without entering a pending queue.
- **FR-008**: Outgoing transactions (withdrawal, transfer, bill payment) submitted by the account manager MUST enter a "Pending" state and NOT modify the business account balance until the authoriser approves them.
- **FR-009**: The authoriser MUST have an in-app pending transactions view listing all pending transactions for their linked business account, with approve and reject actions for each entry.
- **FR-009a**: When the authoriser logs in and pending transactions exist for their business account, their dashboard or navigation MUST display a visible link/button to the pending transactions queue. This control MUST NOT appear when no pending transactions exist.
- **FR-010**: When an authoriser approves a pending transaction, the transaction MUST execute immediately — the business account balance MUST update and the transaction MUST be removed from the pending queue.
- **FR-011**: When an authoriser rejects a pending transaction, the transaction MUST be cancelled, removed from the pending queue, and recorded in the business account transaction history with status "Rejected".

### Key Entities

- **BusinessAccount**: New standalone entity (not a login account); stores business name, UEN, street, city, postal code, and balance. One per business.
- **AccountManager**: A `User` record auto-created per business account; credentials derived from business name. Linked 1:1 to a `BusinessAccount`. Can submit transactions on behalf of the business account.
- **Authoriser**: A `User` record auto-created per business account; credentials derived from business name. Linked 1:1 to a `BusinessAccount`. Can approve or reject pending outgoing transactions.
- **PendingTransaction**: Represents an outgoing transaction (withdrawal, transfer, bill payment) submitted by the account manager that has not yet been approved or rejected. Transitions to executed (on approval) or "Rejected" (on rejection).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A business account can be created in under 2 minutes from landing on `/business/create`, including viewing the generated credentials.
- **SC-002**: 100% of business account creation attempts either succeed (producing manager + authoriser credentials) or return clear field-level errors — no silent failures.
- **SC-003**: 100% of outgoing business account transactions enter "Pending" state upon account manager submission and are only executed after authoriser approval; no outgoing transaction bypasses the pending queue.
- **SC-004**: 100% of deposit transactions submitted by the account manager execute immediately without entering the pending queue.
- **SC-005**: Duplicate UEN submissions are rejected with a user-facing error in 100% of cases.

## Clarifications

### Session 2026-05-25 (Revised Model)

- Q: How are account manager and authoriser login credentials determined when a business account is created? → A: Auto-generated from the business name (e.g. `manager.<bizname>@demo.com`), shown on-screen once after creation — no manual setup required.
- Q: Where does the business account creation form live? → A: Dedicated public page (e.g. `/business/create`), no login required — accessible without an existing user session.
- Q: Which transaction types can the account manager submit for the business account? → A: All types — deposits execute immediately; outgoing transactions (withdrawal, transfer, bill payment) enter pending state and require authoriser approval.
- Q: How many authorisers does a business account have? → A: Exactly one — the mock SQL creates a single authoriser account per business account; multi-authoriser support is out of scope.
- Q: Can one account manager manage multiple business accounts? → A: No — one account manager per business account (1:1); no business account selector needed in the manager UI.
- Q: How are demo phone numbers generated for auto-created manager and authoriser users? → A: Sequential counter — manager gets the next odd slot starting at 80000001, authoriser gets the next even slot starting at 80000002; guarantees uniqueness and is clearly demo data.

### Session 2026-05-25

- Q: Do all transaction types require authoriser approval on a business account? → A: No — only outgoing transactions (withdrawal, transfer, bill payment) require approval; deposits execute immediately.
- Q: What happens to a pending transaction once an authoriser approves it? → A: It executes immediately and is removed from the pending queue; it must no longer appear as pending in the business account view.
- Q: What happens when an authoriser rejects a pending transaction? → A: Cancelled and removed from pending queue; appears in the business account transaction history as "Rejected".
- Q: Can the business account owner cancel a pending transaction before an authoriser acts on it? → A: No — once submitted, a pending transaction can only be approved or rejected by an authoriser.
- Q: How does an authoriser navigate to their approval queue? → A: A button or link to the authoriser queue must be visible on the authoriser's dashboard/navigation whenever there are pending transactions awaiting their action.
- Q: When no authoriser is assigned and a user attempts an outgoing transaction, should the transaction enter pending state or be blocked entirely? → A: Blocked entirely — no pending transaction is created; user is prompted to add an authoriser first (FR-015).
- Q: At what point in the UI should the "no authoriser" block appear? → A: Two points — a dismissible warning banner on the dashboard (reappears on next login if unresolved) and a block at form submission with an error message and link to manage authorisers.
- Q: What should the "no authoriser" prompt contain on form submission? → A: Error message plus a direct link to the manage authorisers page.
- Q: What happens to existing pending transactions when the last authoriser is removed? → A: Automatically cancelled and recorded as "Cancelled" in transaction history (FR-016).

### Session 2026-05-24

- Q: When a business account transaction requires authoriser approval, how does the authoriser review and act on it? → A: In-app pending queue — authoriser logs in and approves/rejects within the app.
- Q: Does the $7,000 minimum apply only at registration or must the account maintain it at all times? → A: Registration-only — $7,000 is required as the initial deposit only.
- Q: Who is the authoriser for a business account — how are they designated? → A: Admin-assigned — a platform admin designates the authoriser after account creation.
- Q: Who can add/assign the authoriser to a business account? → A: Business account owner — assigns their authoriser by phone number from account settings.
- Q: Does the authoriser need to be an existing registered user? → A: Yes — phone number must match an existing registered user; error shown if not found.
- Q: How is the transaction request communicated to the authoriser? → A: In-app only — authoriser logs in and reviews the pending queue; no email or SMS notification.
- Q: Can a business account have more than one authoriser? → A: Yes — multiple authorisers allowed; any one approval is sufficient to execute the transaction.
- Q: Should SC-003 be updated to reflect the authoriser approval step for business transactions? → A: Yes — replace SC-003 with a criterion measuring the pending/approval flow.
- Q: How should the business address be captured? → A: Structured fields — street, city, postal code.
- Q: Should the system validate UEN format against Singapore's standard? → A: No — accept any non-empty alphanumeric string; defer format rules to later.

## Assumptions

- "UEN" (Unique Entity Number) is the business identifier. Any non-empty alphanumeric string is accepted; format validation is deferred to a future version.
- The business account is NOT a login account; it is a standalone entity managed by the auto-created account manager user.
- Account manager and authoriser accounts are created via mock SQL on business account creation — they are not real registration flows.
- Generated credentials are shown once on the confirmation screen; there is no password reset flow in this version.
- Each business account has exactly one account manager and exactly one authoriser, both linked 1:1.
- Business name is a free-text field; no external business registry lookup or verification is required.
- Mobile responsiveness is expected to the same standard as the existing sign-up form.
