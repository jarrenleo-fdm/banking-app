# View and Form Contracts: UX Enhancements

These contracts describe the user-facing web flows affected by the UX enhancement feature. They are written at the route/form behavior level so implementation can remain aligned with server-rendered templates.

---

## Signup

**Route**: `GET/POST /accounts/signup/`

**GET behavior**:
- Display registration fields for name, username, email address, phone number, password, password confirmation, and optional initial balance.
- Display password criteria guidance near the password field.

**POST behavior**:
- Validate password complexity with the same criteria shown in the UI.
- Validate optional initial balance as a non-negative decimal amount.
- Blank or explicit zero initial balance creates the account at `0.00`.
- Positive initial balance is applied through the existing deposit behavior after account creation.
- On success, redirect to login with a success message.
- On validation failure, redisplay the form with field-specific errors and no account creation.

---

## Password Reset Confirm

**Route**: `GET/POST /accounts/password-reset/confirm/<uidb64>/<token>/`

**GET behavior**:
- Display new password fields and the same criteria guidance used during signup.

**POST behavior**:
- Validate password complexity with the same backend rules used during signup.
- Reject unmet password criteria with form errors.
- On success, complete the password reset using the existing password reset flow.

---

## User Details

**Route**: `GET/POST /accounts/profile/`

**Access**:
- Requires an authenticated user.
- Anonymous users are redirected to login.

**GET behavior**:
- Display the current user's name, username, email address, and phone number.
- Name, username, email address, and phone number are editable.
- Display password change controls for current password, new password, and new password confirmation without displaying the current password value.
- Display the same password criteria guidance used during signup and password reset near the new password field.

**POST behavior**:
- Accept edits for name, username, email address, and phone number.
- Accept password change submissions that include current password, new password, and new password confirmation.
- Validate username format and uniqueness before saving.
- Normalize email address to lowercase.
- Normalize phone-number spaces and hyphens before validation.
- Validate phone number using the same registration format rules.
- Reject username, email, or phone number conflicts with another account.
- Validate password changes against the current password, new password confirmation, and the shared password criteria.
- If any submitted field is invalid, keep the existing saved details unchanged and redisplay field-specific errors.
- If profile fields are valid, save the changed details, emit a non-PII audit/log event with changed field names, and show a success message.
- If password fields are valid, save the changed password, keep the user authenticated, emit a non-PII audit/log event for a password change, and show a success message.

**Postconditions**:
- Successful changes are visible immediately when the page reloads.
- Future login attempts use the updated username and password.
- Future transfer lookup by phone number uses the updated phone number.
- Existing transaction history remains readable after profile updates.

---

## Transaction History

**Route**: `GET /banking/transactions/`

**Behavior**:
- Every transaction entry displays a unique transaction ID.
- Transfer entries display directional counterparty labels: sender for incoming transfers and recipient for outgoing transfers.
- Transfer descriptions are displayed only when present.
- Deposit and withdrawal entries without a counterparty do not show an empty counterparty placeholder.

---

## Transfer

**Route**: `GET/POST /banking/transfer/` or dashboard transfer form

**Behavior**:
- Display an optional transfer description field with a 200 character limit.
- Valid descriptions are saved to both sender and recipient transaction records.
- Empty descriptions do not create empty description labels in history.
