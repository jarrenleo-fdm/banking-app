# Feature Specification: Billing System

**Feature Branch**: `004-billing-system`  
**Created**: 2026-05-21  
**Status**: Draft  
**Input**: User description: "Add a billing system where we can use our accounts pay for bills"

## Clarifications

### Session 2026-05-21

- Q: Which predefined biller categories should be available for selection? → A: Electricity · Water & Utilities · Internet & Broadband · Telecommunications · Town Council / Maintenance (5 fixed categories; free-text biller names are not supported).
- Q: What is the uniqueness scope for the mandatory reference field? → A: Unique per user + category — two billers of the same category under the same user cannot share the same reference; the same reference string may appear under different categories.

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Pay a Bill (Priority: P1)

A logged-in user selects a biller (e.g., electricity, internet), enters the amount they want to pay, and confirms the payment. The amount is deducted from their account balance and a record of the payment is created.

**Why this priority**: This is the core of the feature. Every other story depends on the ability to execute a bill payment.

**Independent Test**: Can be fully tested by navigating to the billing section, selecting a biller, entering an amount, confirming, and verifying the account balance decreased and a bill payment record appears in the transaction list.

**Acceptance Scenarios**:

1. **Given** a logged-in user has sufficient balance, **When** they select a biller and submit a payment, **Then** the account balance is reduced by the payment amount and a bill payment record is created.
2. **Given** a logged-in user has insufficient balance, **When** they attempt to submit a bill payment, **Then** the payment is rejected with a clear error message and their balance is unchanged.
3. **Given** a logged-in user submits a payment with a zero or negative amount, **When** they attempt to submit, **Then** the form displays a validation error and no payment is processed.

---

### User Story 2 - Manage Saved Billers (Priority: P2)

A user can add, view, and remove billers by selecting from a fixed list of 5 predefined categories: **Electricity**, **Water & Utilities**, **Internet & Broadband**, **Telecommunications**, and **Town Council / Maintenance**. A reference/account number is **mandatory** for each saved biller and must be unique within the same category for that user — this ensures multiple billers of the same category remain distinguishable. Saved billers make future payments faster without requiring the user to type any names.

**Why this priority**: Without saved billers, every payment requires manually entering payee details, which is error-prone and slow. Saved billers are the foundation of a usable billing experience.

**Independent Test**: Can be fully tested by selecting a biller category, entering a reference, saving, verifying the biller appears in the list, then removing it and confirming it no longer appears.

**Acceptance Scenarios**:

1. **Given** a logged-in user is on the billing page, **When** they select a biller category from the predefined list and enter a reference, **Then** the biller is saved and appears in their billers list showing the category name and reference.
2. **Given** a logged-in user has saved billers, **When** they view the billing page, **Then** all saved billers are listed by category name and can be selected for payment.
3. **Given** a logged-in user selects a saved biller for deletion, **When** they confirm the removal, **Then** the biller is removed from their list and cannot be selected for future payments.
4. **Given** a logged-in user attempts to submit the add-biller form without selecting a category, **When** they submit, **Then** a validation error is shown and no biller is saved.
5. **Given** a logged-in user attempts to submit the add-biller form without entering a reference, **When** they submit, **Then** a validation error is shown and no biller is saved.
6. **Given** a logged-in user already has a saved biller of a given category with a specific reference, **When** they attempt to add another biller of the same category with the same reference, **Then** a validation error is shown indicating the reference must be unique for that category and no duplicate biller is saved.

---

### User Story 3 - View Bill Payment History (Priority: P3)

A user can view a list of all past bill payments including the biller name, amount paid, date, and payment status, giving them a clear record of what they have paid.

**Why this priority**: Payment history is essential for accountability and reconciliation, but the core payment flow works without it on day one.

**Independent Test**: Can be fully tested by making at least one bill payment and confirming it appears in the bill payment history with the correct biller, amount, and date.

**Acceptance Scenarios**:

1. **Given** a logged-in user has made bill payments, **When** they view their bill payment history, **Then** all payments are listed with biller name, amount, and date, ordered most-recent first.
2. **Given** a logged-in user has never made a bill payment, **When** they view their bill payment history, **Then** an empty state message is displayed.
3. **Given** a logged-in user views their bill payment history, **When** they inspect a specific entry, **Then** the entry matches the corresponding deduction visible on the main transactions page.

---

### Edge Cases

- What happens when a user attempts a bill payment that would reduce their balance below zero?
- Saving two billers of the same category is allowed provided their references differ; attempting to save with an already-used category + reference combination returns a validation error.
- How does the system behave if a user deletes a biller that has associated payment history?
- What happens if a user navigates away mid-payment before confirming?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST allow users to add a biller by selecting one of five predefined categories (Electricity, Water & Utilities, Internet & Broadband, Telecommunications, Town Council / Maintenance) and entering a mandatory reference/account number. Free-text biller names are not supported.
- **FR-001a**: The reference/account number MUST be mandatory — the add-biller form MUST NOT be submittable without it.
- **FR-001b**: The reference MUST be unique per user and category — the system MUST reject attempts to save a second biller with the same category and reference for the same user.
- **FR-002**: The system MUST display a list of all billers saved by the logged-in user.
- **FR-003**: The system MUST allow users to remove a saved biller.
- **FR-004**: The system MUST allow users to pay a bill by selecting a saved biller, entering an amount, and confirming the payment.
- **FR-005**: The system MUST reject bill payments where the requested amount exceeds the user's current account balance.
- **FR-006**: The system MUST reject bill payments with an amount of zero or less.
- **FR-007**: On successful payment, the system MUST deduct the amount from the user's account balance and record the payment as a transaction.
- **FR-008**: The system MUST display a bill payment history showing biller name, amount, and date for each payment made by the logged-in user.
- **FR-009**: Bill payments MUST appear in the existing transaction history, identifiable as bill payments.
- **FR-010**: The system MUST prevent users from accessing or modifying another user's billers or payment history.

### Key Entities

- **Biller**: A payee saved by a user; has a category (one of five predefined values: Electricity, Water & Utilities, Internet & Broadband, Telecommunications, Town Council / Maintenance), a mandatory reference/account number (free-text, unique per user + category), and belongs to one user. The category is selected, not typed.
- **Bill Payment**: A record of a completed payment; links to a biller, the paying account, the amount, and the timestamp. Maps to a transaction entry.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can complete a bill payment in under 2 minutes from the billing page.
- **SC-002**: 100% of successful bill payments result in a corresponding balance deduction and a transaction record — no silent failures.
- **SC-003**: Zero bill payments are processed when the account has insufficient funds.
- **SC-004**: Users can add and remove billers without errors across all supported account types (personal and business).
- **SC-005**: All bill payments appear in the transaction history with enough detail to distinguish them from deposits, withdrawals, and transfers.

## Assumptions

- Both personal and business account holders can use the billing system; there is no account-type restriction.
- Billers are private to the user who created them — they are not shared across users or accounts.
- Payments are immediate and non-reversible once confirmed; no scheduled or recurring billing is in scope for this version.
- A single account per user exists (as per the current data model); payments are always drawn from that account.
- Biller names are not free-text — users must select from the five predefined categories. The reference field (e.g., an account or customer number with the biller) is mandatory, free-text, and must be unique per user and category.
- A user may save the same category more than once provided each entry has a distinct reference (e.g., two Electricity billers for two premises with different account numbers).
- Deleting a biller retains its historical payment records for auditing purposes; only the biller entry itself is removed.
