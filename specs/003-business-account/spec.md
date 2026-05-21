# Feature Specification: Business Account Registration

**Feature Branch**: `003-business-account`  
**Created**: 2026-05-21  
**Status**: Draft  
**Input**: User description: "Add the option to create a business account"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Register Business Account (Priority: P1)

A user representing a business visits the sign-up page and selects "Business Account" as their account type. They provide their personal details alongside business-specific information (company name and business registration number), then complete registration to receive a functioning business account.

**Why this priority**: This is the core of the feature. Without the ability to register a business account, all other stories are irrelevant.

**Independent Test**: Can be fully tested by navigating to sign-up, selecting "Business Account", filling in all fields, submitting, and confirming a business account is created and accessible.

**Acceptance Scenarios**:

1. **Given** a visitor is on the sign-up page, **When** they select "Business Account", **Then** the form expands to show business-specific fields (company name, business registration number) in addition to the standard personal fields.
2. **Given** a visitor has filled in all required fields for a business account, **When** they submit the form, **Then** their account is created, they are logged in, and their dashboard reflects a business account.
3. **Given** a visitor selects "Business Account" but omits the company name or registration number, **When** they submit, **Then** the form displays clear validation errors and does not create an account.

---

### User Story 2 - Distinguish Account Type on Dashboard (Priority: P2)

After logging in, a business account holder can clearly see that their account is a business account (e.g., a label or badge showing "Business Account") rather than the default personal account view.

**Why this priority**: Business account holders need confirmation that their account is correctly identified; it also sets the stage for future business-specific features.

**Independent Test**: Can be tested by creating a business account via the registration flow and checking that the dashboard displays a "Business" identifier.

**Acceptance Scenarios**:

1. **Given** a business account holder is logged in, **When** they view the dashboard, **Then** the account type is clearly labeled as "Business".
2. **Given** a personal account holder is logged in, **When** they view the dashboard, **Then** the account type is labeled as "Personal" (or unchanged from current behaviour).

---

### User Story 3 - Select Account Type at Sign-Up (Priority: P3)

A visitor can clearly choose between "Personal" and "Business" account types at the start of registration, with both options presented in a user-friendly way that explains what each type is for.

**Why this priority**: Clear account type selection reduces user error and improves registration UX, but the system still functions without explicit labelling as long as the business fields are present.

**Independent Test**: Can be tested by visiting the sign-up page and confirming that both Personal and Business options are visible and toggling between them shows the appropriate fields.

**Acceptance Scenarios**:

1. **Given** a visitor is on the sign-up page, **When** they view it for the first time, **Then** "Personal" is selected by default and only standard fields are visible.
2. **Given** a visitor toggles to "Business Account", **When** the selection changes, **Then** the business-specific fields appear without a page reload.
3. **Given** a visitor toggles back to "Personal" after selecting "Business", **When** the selection changes, **Then** the business-specific fields are hidden.

---

### Edge Cases

- What happens when a business registration number is submitted that is already associated with another account?
- What happens when a user submits the form with a company name that contains only whitespace?
- How does the system handle a business registration number in an invalid format?
- What happens if a user attempts to access the registration page while already logged in?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The sign-up form MUST offer a choice between "Personal" and "Business" account types.
- **FR-002**: When "Business" is selected, the form MUST display additional required fields: company name and business registration number.
- **FR-003**: The system MUST validate that company name and business registration number are not empty for business account registrations.
- **FR-004**: Business registration numbers MUST be unique across all accounts.
- **FR-005**: The system MUST associate the account type (personal or business) with the user's account upon creation.
- **FR-006**: The dashboard MUST display the account type label ("Personal" or "Business") to the logged-in user.
- **FR-007**: Business account holders MUST have access to all existing banking operations (deposit, withdrawal, transfer) without restriction.
- **FR-008**: The system MUST prevent creation of an account with a duplicate business registration number and surface a meaningful validation error.

### Key Entities

- **User**: Existing entity; gains an `account_type` field (personal or business).
- **Business Profile**: New entity linked to a User; stores company name and business registration number. Only exists for business account users.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A visitor can complete business account registration in under 3 minutes from landing on the sign-up page.
- **SC-002**: 100% of submitted business registrations either create a valid business account or return a clear, field-level error — no silent failures.
- **SC-003**: Business account holders can access all banking operations (deposit, withdrawal, transfer) without additional steps beyond what personal account holders perform.
- **SC-004**: The account type label is visible on the dashboard for 100% of logged-in users (both personal and business).
- **SC-005**: Duplicate business registration number submissions are rejected with a user-facing error in 100% of cases.

## Assumptions

- "Business registration number" refers to a government-issued company registration identifier; format validation will follow a reasonable alphanumeric pattern unless a specific country standard is provided later.
- Existing personal account holders cannot convert their account to a business account; conversion is out of scope for this feature.
- Business accounts share the same transaction limits and fee structures as personal accounts in this version.
- The company name is a free-text field; no external business registry lookup or verification is required.
- A single user (login) maps to one account type; a user cannot hold both a personal and a business account simultaneously.
- Mobile responsiveness is expected to the same standard as the existing sign-up form.
