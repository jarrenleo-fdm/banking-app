# Service Layer Contracts: UX Enhancements

The service layer in `banking/services.py` is the internal contract boundary between views and the data layer. One function signature changes in this feature.

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

These functions are not modified. Their signatures and behaviour remain as-is.

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

Registered in `settings.AUTH_PASSWORD_VALIDATORS`. Called automatically by `validate_password()` in `RegistrationForm.clean()` and by Django's built-in `SetPasswordForm` during password reset.
