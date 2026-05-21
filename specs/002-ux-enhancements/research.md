# Research: UX Enhancements

## Existing Codebase Findings

### Decision: No database migrations required
- **Rationale**: `Transaction.description` (CharField max_length=200, blank=True) and `Transaction.counterparty` (FK to Account, null/blank=True) already exist in `banking/migrations/0001_initial.py`. The data model is complete; only application logic and templates need updating.
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
- **Rationale**: Account creation is triggered by a `post_save` signal on the User model (`banking/models.py:69`) which always starts with `balance=0`. Modifying the signal to accept an initial balance would require non-trivial signal parameter threading. The simpler approach: after `form.save()` in `signup_view`, if `initial_balance > 0`, fetch the newly created account and update its balance in a single `save(update_fields=["balance"])`. This is safe because the signal and the view operate sequentially in the same request thread.
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
