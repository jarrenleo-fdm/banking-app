# Research: UX Enhancements

## Existing Codebase Findings

### Decision: No database migrations required
- **Rationale**: `Transaction.description` (CharField max_length=200, blank=True), `Transaction.counterparty` (FK to Account, null/blank=True), and the editable user identity/contact fields (`CustomUser.name`, `CustomUser.email`, `CustomUser.phone_number`) already exist. The data model is complete; only application logic, forms, views, and templates need updating.
- **Alternatives considered**: Adding new fields — rejected; fields are already present.

### Decision: Add a custom password complexity validator
- **Rationale**: Django's current `AUTH_PASSWORD_VALIDATORS` in `settings.py` enforce minimum length (8), similarity to user attributes, common passwords, and all-numeric rejection. They do **not** enforce uppercase, lowercase, digit presence, or special character requirements. Displaying these as UI criteria while the backend does not enforce them would mislead users and constitute a security gap (OWASP A07 — Identification and Authentication Failures). A custom validator aligns backend enforcement with UI feedback.
- **Alternatives considered**: UI-only criteria that only match existing validators — rejected because it creates a false sense of security; the spec explicitly lists these four criteria and the constitution mandates OWASP Top 10 mitigation.

### Decision: Prototype / Learning Tier
- **Rationale**: Project uses SQLite3 (not PostgreSQL) and `@transaction.atomic` without `select_for_update()`. This matches the constitution's Prototype/Learning tier definition. SonarQube is not required; compensating controls (flake8, pylint, bandit via pre-commit) are already configured.
- **Alternatives considered**: Production tier — not applicable until PostgreSQL is adopted.

### Decision: Transfer description passed through service layer
- **Rationale**: `transfer()` in `banking/services.py` currently creates both `TRANSFER_OUT` and `TRANSFER_IN` records without a description. The description must be accepted as a parameter and written to both transaction records to satisfy FR-007 and FR-008. The `TransferForm` must expose the optional field; the view passes it to the service.
- **Alternatives considered**: Storing description only on the TRANSFER_OUT record — rejected; FR-008 requires it to appear for both sender and recipient.

### Decision: Initial balance set post-signal in signup_view
- **Rationale**: Account creation is triggered by a `post_save` signal on the User model, which starts with `balance=0`. A non-zero initial balance should go through the existing `deposit()` service so the balance is reflected in immutable transaction history and reconciles with the account balance. Blank and explicit zero inputs leave the account at the signal-created zero balance.
- **Alternatives considered**: Modifying the signal — rejected (over-engineering); creating Account directly in the view without the signal — rejected (breaks the existing guarantee for non-signup account creation paths).

### Decision: Password criteria checklist implemented as inline JavaScript
- **Rationale**: The project has no JavaScript build pipeline; it uses plain static files (`static/css/styles.css`). A small inline `<script>` block or a single static JS file is sufficient and keeps the dependency footprint at zero.
- **Alternatives considered**: A frontend framework — rejected (not present in the project); server-side rendering only — rejected (no real-time feedback without JS).

### Decision: Password reset confirm form uses Django's SetPasswordForm
- **Rationale**: Django's built-in `PasswordResetConfirmView` renders `SetPasswordForm` which already integrates with `AUTH_PASSWORD_VALIDATORS`. Adding the custom validator to settings automatically applies it to the password reset flow. The template `password_reset_confirm.html` uses `{{ form.as_p }}`; the criteria checklist can be added to this template the same way as signup.
- **Alternatives considered**: A custom reset view — rejected; unnecessary given Django's built-in handles everything once the validator is registered.

### Decision: Transaction ID shown as model primary key
- **Rationale**: Django's `BigAutoField` primary key (`transaction.pk`) is unique, stable, and already present. No separate UUID field is needed for the Prototype tier.
- **Alternatives considered**: UUID field — useful for production obfuscation but adds a migration and is out of scope for Prototype tier.

### Decision: User details and credential updates handled in the accounts app
- **Rationale**: Name, username, email address, phone number, login, signup, password reset, and password changes are all owned by `accounts/`. The new flow should use an authenticated account-management page backed by forms initialized from `request.user`. Keeping it in `accounts/` avoids mixing identity/profile behavior into banking money-movement views.
- **Alternatives considered**: Adding the form to the banking dashboard — rejected because identity editing is not a banking transaction and would make the dashboard less focused; adding a banking service layer function — rejected because this is user-record validation/update, not shared money movement logic.

### Decision: Username is editable with the same identifier safeguards as signup
- **Rationale**: The updated spec requires users to change their username. The profile form should validate username format with the existing custom user constraints, normalize consistently with the model, and reject conflicts with other accounts while excluding the current user from duplicate checks. Existing transaction history remains tied to account records, so changing the username should not alter historical transaction records.
- **Alternatives considered**: Keeping username read-only — rejected because it contradicts the updated feature scope; creating a separate username-change endpoint — rejected because the profile page already owns identity updates and a separate route would add unnecessary navigation.

### Decision: Password change reuses Django's authenticated password-change form
- **Rationale**: Django's `PasswordChangeForm` validates the current password, checks new-password confirmation, and runs `AUTH_PASSWORD_VALIDATORS`, including the custom complexity validator. It also supports session-auth-hash updates so users are not logged out after a successful password change.
- **Alternatives considered**: Building custom password comparison logic in the profile form — rejected because Django already provides the safer, tested behavior; requiring password reset for signed-in changes — rejected because the updated spec requires signed-in password changes.

### Decision: Reuse registration contact validation rules for profile updates
- **Rationale**: Email must remain normalized to lowercase and unique. Phone numbers must remain Singapore-style 8 digit strings beginning with 8 or 9, with spaces and hyphens normalized before uniqueness checks. The profile form should exclude the current user's record when checking uniqueness so unchanged values remain valid.
- **Alternatives considered**: Looser validation for existing users — rejected because transfer lookup depends on reliable phone-number format and uniqueness.

### Decision: Log profile and credential updates without raw PII
- **Rationale**: Updating user identity/contact details, username, or password is security-relevant. A lightweight audit/log event can record the acting user id and the field names or credential category changed without logging raw email addresses, phone numbers, usernames, or password material, satisfying auditability expectations without a schema migration.
- **Alternatives considered**: Adding a database audit table — stronger for production but out of scope for this prototype UX enhancement; logging raw before/after values — rejected because logs must not contain raw personal data.
