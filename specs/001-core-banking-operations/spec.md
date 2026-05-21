# Feature Specification: Core Banking Operations

**Feature Branch**: `001-core-banking-operations`
**Created**: 2026-05-21
**Status**: Draft
**Input**: User description: "The banking app should have a login in / sign up page. Once logged in, the user should be greeted with a dashboard showing the amount of money he/she has. The user should be to deposit and withdraw money, send and receive money, be able to view transaction history. User shouldn't be able to have a bank overdraft."

## Clarifications

### Session 2026-05-21

- Q: Is an email address still collected at registration? → A: Yes — email is still collected for notifications and account identity; the username (not email) is the login credential; both username and email must be unique.
- Q: How does a sender identify a transfer recipient? → A: By phone number — a sender sends money by entering the recipient's phone number, and registration now collects a unique phone number for each account. (Updated from an earlier "by username" decision.)
- Q: Is the username case-sensitive? → A: Case-insensitive — username matching ignores case for login and registration uniqueness; display preserves the user's chosen casing.
- Q: What phone number format will the app use? → A: National/local format for a single country or region — numbers are entered without a country code and normalized to one canonical form for storage, uniqueness, and lookup.
- Q: How is the password reset delivered to the user? → A: By email — a single-use, time-limited reset link is sent to the user's registered email address; the reset request reveals nothing about whether an account exists.
- Q: Is the phone number verified at registration? → A: No — the phone number is accepted as entered after format validation; phone verification (e.g., SMS confirmation) is out of scope for this version.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Open an Account and Manage Personal Funds (Priority: P1)

A new customer creates an account, logs in, and lands on a dashboard that shows their current balance. From there they can deposit money into their account and withdraw money from it, and the system never lets their balance fall below zero.

**Why this priority**: This is the minimum viable banking product. Without the ability to create an account, sign in securely, see a balance, and move one's own money in and out, the application delivers no value and no other feature is reachable.

**Independent Test**: Register a new user, log in with those credentials, confirm the dashboard shows a zero starting balance, deposit an amount and confirm the balance rises by exactly that amount, withdraw a smaller amount and confirm the balance falls correctly, then attempt to withdraw more than the balance and confirm the withdrawal is blocked.

**Acceptance Scenarios**:

1. **Given** a visitor on the sign-up page, **When** they submit valid details with a username, email address, and phone number not already in use, **Then** a new account is created with a zero balance and they can log in.
2. **Given** a visitor on the sign-up page, **When** they submit a username, email address, or phone number that already belongs to an account, **Then** registration is rejected with a clear message.
3. **Given** a registered user on the login page, **When** they submit correct credentials, **Then** they are signed in and taken to their dashboard showing their current balance.
4. **Given** a registered user on the login page, **When** they submit incorrect credentials, **Then** login is rejected without revealing whether the username or the password was wrong.
5. **Given** an unauthenticated visitor, **When** they try to open the dashboard directly, **Then** they are required to log in first.
6. **Given** a logged-in user, **When** they deposit a positive amount, **Then** their balance increases by exactly that amount.
7. **Given** a logged-in user with sufficient funds, **When** they withdraw a positive amount, **Then** their balance decreases by exactly that amount.
8. **Given** a logged-in user, **When** they attempt to withdraw more than their current balance, **Then** the withdrawal is rejected and the balance is unchanged.
9. **Given** a logged-in user, **When** they attempt to deposit or withdraw a zero or negative amount, **Then** the request is rejected.
10. **Given** a registered user who has forgotten their password, **When** they request a reset by submitting their email address, **Then** a single-use, time-limited reset link is sent to that email address.
11. **Given** a user who has a valid, unexpired reset link, **When** they set a new password that meets the strength rules, **Then** the password is updated and they can log in with it.

---

### User Story 2 - Send and Receive Money (Priority: P2)

A logged-in customer sends money from their account to another registered customer. The recipient's balance increases by the amount sent, and the sender's balance decreases by the same amount. The system never lets a transfer push the sender's balance below zero.

**Why this priority**: Peer-to-peer transfer turns a personal money store into a payment tool and is the second most valuable capability. It depends on the accounts and balances established in P1.

**Independent Test**: With two registered accounts, send a valid amount from one to the other, confirm the sender's balance decreases and the recipient's balance increases by the same amount, then attempt to send more than the sender's balance and confirm the transfer is blocked.

**Acceptance Scenarios**:

1. **Given** a logged-in sender with sufficient funds and a valid recipient, **When** they send a positive amount, **Then** the sender's balance decreases and the recipient's balance increases by that amount.
2. **Given** a logged-in sender, **When** they attempt to send more than their current balance, **Then** the transfer is rejected and no balances change.
3. **Given** a logged-in sender, **When** they name a recipient who is not a registered user, **Then** the transfer is rejected with a clear message.
4. **Given** a logged-in sender, **When** they name their own account as the recipient, **Then** the transfer is rejected.
5. **Given** a logged-in sender, **When** they attempt to send a zero or negative amount, **Then** the transfer is rejected.
6. **Given** a registered recipient, **When** another user sends them money, **Then** their balance increases by the amount received.

---

### User Story 3 - View Transaction History (Priority: P3)

A logged-in customer opens their transaction history and sees a chronological record of every deposit, withdrawal, and transfer on their account, so they can verify their balance and review past activity.

**Why this priority**: A transaction history gives customers transparency and confidence in their balance. It is a read-only view that depends on transactions created by P1 and P2, so it is delivered last.

**Independent Test**: After performing several deposits, withdrawals, and transfers, open the transaction history and confirm every operation appears with the correct type, amount, date, and resulting balance, listed most recent first.

**Acceptance Scenarios**:

1. **Given** a user who has made transactions, **When** they open their transaction history, **Then** all of their transactions are listed with the most recent first.
2. **Given** a transaction in the history, **When** the user views it, **Then** its type, amount, date and time, and resulting balance are shown.
3. **Given** a transfer between two users, **When** either party views their history, **Then** the transfer appears and identifies the other party.
4. **Given** a user who has made no transactions, **When** they open their history, **Then** a clear message stating they have no transactions yet is shown.
5. **Given** two different users, **When** each opens their transaction history, **Then** each sees only the transactions involving their own account.

---

### Edge Cases

- What happens when a user attempts to withdraw or send more than their available balance? The operation is rejected and the balance is never allowed to become negative.
- What happens when two withdrawals or transfers on the same account occur at the same time? Each operation is evaluated against the true current balance, and the account is never overdrawn.
- What happens when a deposit, withdrawal, or transfer amount is zero, negative, or otherwise invalid? The request is rejected before any balance changes.
- What happens when a transfer recipient does not exist, or the sender names their own account as the recipient? The transfer is rejected with a clear message and no balances change.
- What happens when a user's session expires partway through an action? The user must log in again, and the action is not applied until they are authenticated.
- What happens when someone registers with a username, email address, or phone number that already belongs to an account? Registration is rejected.
- What happens when a transfer cannot complete after the sender has been debited? This is not permitted — a transfer either completes fully for both parties or is fully reversed.
- What happens when a user tries to view another user's balance or transactions? Access is denied; each user sees only their own data.
- What happens when a user opens a password reset link that has expired or has already been used? The link is rejected, the password is left unchanged, and the user must request a new reset.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST allow a visitor to register a new account by providing their name, username, email address, phone number, and a password.
- **FR-002**: System MUST reject registration when the provided username (compared case-insensitively), email address, or phone number is already associated with an existing account.
- **FR-003**: System MUST enforce minimum password-strength rules when a password is set.
- **FR-004**: System MUST allow a registered user to log in using their username (matched case-insensitively) and password.
- **FR-005**: System MUST reject login attempts with invalid credentials and MUST NOT reveal whether the username or the password was incorrect.
- **FR-006**: System MUST keep a user authenticated for the duration of their session and MUST allow them to log out, ending the session.
- **FR-007**: System MUST require authentication for all account features, and each user MUST be able to access only their own account, balance, and transactions.
- **FR-008**: System MUST display the user's current account balance on their dashboard after they log in.
- **FR-009**: System MUST set a newly registered account's starting balance to zero.
- **FR-010**: System MUST show the updated balance after every deposit, withdrawal, or transfer.
- **FR-011**: System MUST allow an authenticated user to deposit a positive amount into their own account, increasing the balance by that amount.
- **FR-012**: System MUST allow an authenticated user to withdraw a positive amount from their own account, decreasing the balance by that amount.
- **FR-013**: System MUST reject any withdrawal that would cause the account balance to fall below zero.
- **FR-014**: System MUST reject any deposit or withdrawal whose amount is zero or negative.
- **FR-015**: System MUST allow an authenticated user to send a positive amount of money to another registered user identified by their phone number.
- **FR-016**: System MUST decrease the sender's balance and increase the recipient's balance by the transferred amount when a transfer succeeds.
- **FR-017**: System MUST reject any transfer that would cause the sender's balance to fall below zero.
- **FR-018**: System MUST reject a transfer when no registered user matches the specified recipient.
- **FR-019**: System MUST reject a transfer when the sender and the recipient are the same account.
- **FR-020**: System MUST reject any transfer whose amount is zero or negative.
- **FR-021**: System MUST apply each transfer as a single all-or-nothing operation, so the sender's debit and the recipient's credit either both take effect or neither does.
- **FR-022**: System MUST record every deposit, withdrawal, and transfer as a transaction entry.
- **FR-023**: Each transaction entry MUST include its type, amount, date and time, resulting account balance, and — for transfers — the other party involved.
- **FR-024**: System MUST allow an authenticated user to view their transaction history, showing only transactions involving their own account, ordered with the most recent first.
- **FR-025**: System MUST prevent users from altering or deleting transaction entries.
- **FR-026**: System MUST represent and calculate all monetary amounts exactly, with no rounding errors.
- **FR-027**: System MUST keep each account's balance equal to the net sum of all its recorded transactions at all times.
- **FR-028**: System MUST require a valid phone number in the application's national/local format at registration, normalize every phone number to a single canonical form, and use that canonical form for uniqueness checks and transfer recipient lookup.
- **FR-029**: System MUST allow a user to request a password reset by submitting an email address, and MUST respond identically whether or not an account exists for that address.
- **FR-030**: When a submitted email address matches an existing account, System MUST send a single-use, time-limited password reset link to that email address.
- **FR-031**: System MUST allow a user with a valid, unexpired reset link to set a new password that meets the password-strength rules, and MUST reject any expired, already-used, or invalid reset link.
- **FR-032**: After a successful password reset, System MUST allow login with the new password and MUST end any other active sessions for that account.

### Key Entities

- **User**: A person who owns and accesses a banking account. Identified by a unique username used to log in; also has a unique email address, a unique phone number used to receive transfers, a name, and authentication credentials.
- **Account**: Holds a single user's money. Belongs to exactly one user and has a current balance that must never be negative.
- **Transaction**: An immutable record of one money movement — a deposit or withdrawal affecting one account, or a transfer affecting two. Has a type, amount, date and time, resulting balance, and, for transfers, the counterparty.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A new user can complete registration and reach their dashboard in under 2 minutes.
- **SC-002**: A returning user sees their current balance immediately upon logging in.
- **SC-003**: 100% of withdrawal and transfer attempts that exceed the available balance are prevented — no account ever reaches a negative balance.
- **SC-004**: Every account's balance always equals the net sum of its recorded transactions, verified at any point in time.
- **SC-005**: A user can complete a deposit, withdrawal, or transfer in under 1 minute.
- **SC-006**: A completed transfer is reflected immediately in both the sender's and the recipient's balances.
- **SC-007**: 100% of completed transactions appear in the transaction history with the correct type, amount, and resulting balance.
- **SC-008**: At least 95% of users can complete a deposit, withdrawal, or transfer on their first attempt without errors or assistance.

## Assumptions

- Deposits and withdrawals are simulated balance adjustments within the application; they represent money entering or leaving the account and do not integrate with external banks, card networks, or payment processors in this version.
- Money transfers occur only between two accounts that exist within this application; transfers to external banks or accounts are out of scope.
- The application operates in a single currency.
- Each user has exactly one account.
- A sender identifies a transfer recipient by the recipient's phone number.
- The application serves a single country or region; phone numbers are entered and stored in that region's national format.
- Phone numbers are not verified at registration — the application accepts the number as entered (after format validation) without confirming the registrant controls it; phone verification is out of scope for this version.
- Customer login uses a username and password; multi-factor authentication for customer accounts is out of scope for this version.
- Account balances start at zero when an account is created.
- There are no per-transaction or daily transfer or withdrawal limits beyond the account's available balance.
- Sending money to one's own account is treated as invalid and is rejected.
- Delivering password reset links requires the application to send transactional email; an outbound email capability is in scope for this version.
- Account closure and account deletion are out of scope for this version.
- This feature covers the customer-facing experience only; administrative and back-office functions are out of scope.
- Users access the application through a standard web browser with stable internet connectivity.
