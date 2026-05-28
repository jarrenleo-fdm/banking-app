# Service Layer Contracts: UX Enhancements

The service layer in `banking/services.py` is the internal contract boundary between views and the data layer. One banking service function signature changes in this feature. The user details and credential update flow is handled by the accounts app form/view layer and does not add a banking service contract.

---

## `transfer` (modified)

```
transfer(
    sender_account: Account,
    recipient_phone: str,
    amount: Decimal,
    description: str = "",
) -> tuple[Transaction, Transaction]
```

**Change**: Added optional `description` parameter (default empty string).

**Behaviour**:
- All existing validation and atomicity guarantees are unchanged.
- `description` is written to both the `TRANSFER_OUT` and `TRANSFER_IN` `Transaction` records created by this function.
- Callers that do not provide `description` continue to work without modification (deposit, withdraw, other callers).

**Raises**: `InvalidAmountError`, `InsufficientFundsError`, `RecipientNotFoundError`, `SelfTransferError` — unchanged.

---

## `deposit` / `withdraw` (unchanged)

`withdraw` is not modified. `deposit` keeps its existing signature and validation behavior.

`deposit` is used by registration when an optional initial balance greater than zero is submitted, so the opening balance is reflected in immutable personal transaction history.

---

## `PasswordComplexityValidator` (new)

```
accounts/validators.py

class PasswordComplexityValidator:
    def validate(self, password, user=None) -> None
        # Raises ValidationError if password fails any character class check
    def get_help_text(self) -> str
        # Returns a human-readable description of the requirements
```

Registered in `settings.AUTH_PASSWORD_VALIDATORS`. Called automatically by `validate_password()` in `RegistrationForm.clean()`, Django's built-in `SetPasswordForm` during password reset, and Django's authenticated password-change form.

---

## User details and credential update (no banking service)

No new banking service is introduced for profile updates.

**Behaviour**:
- The accounts form/view layer updates only the authenticated user's `name`, `username`, `email`, and `phone_number`.
- Username, email, and phone-number uniqueness checks exclude the current user and reject conflicts with other accounts.
- Password changes require the authenticated user's current password, a valid new password, and matching confirmation.
- Successful updates emit non-PII audit/log events containing the acting user id and changed field names or credential category only.
