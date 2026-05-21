"""Forms for banking operations."""
from decimal import Decimal

from django import forms
from django.core.validators import RegexValidator


class AmountForm(forms.Form):
    """Shared positive amount form."""

    amount = forms.DecimalField(
        min_value=Decimal("0.01"),
        max_digits=12,
        decimal_places=2,
    )


class DepositForm(AmountForm):
    """Deposit amount form."""


class WithdrawForm(AmountForm):
    """Withdrawal amount form."""


class TransferForm(AmountForm):
    """Transfer recipient and amount form."""

    recipient_phone = forms.CharField(
        max_length=10,
        validators=[RegexValidator(r"^[89]\d{7}$")],
    )

    def clean_recipient_phone(self):
        return (
            self.cleaned_data["recipient_phone"]
            .strip()
            .replace(" ", "")
            .replace("-", "")
        )
