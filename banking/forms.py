"""Forms for banking operations."""
from decimal import Decimal

from django import forms
from django.core.validators import RegexValidator

from .models import Biller


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
    description = forms.CharField(max_length=200, required=False)

    def clean_recipient_phone(self):
        return (
            self.cleaned_data["recipient_phone"]
            .strip()
            .replace(" ", "")
            .replace("-", "")
        )


class BillerForm(forms.Form):
    """Add a new saved biller."""

    name = forms.ChoiceField(choices=Biller.BILLER_CATEGORIES)
    reference = forms.CharField(max_length=100)

    def __init__(self, *args, account=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.account = account

    def clean(self):
        cleaned_data = super().clean()
        name = cleaned_data.get("name")
        reference = cleaned_data.get("reference")
        if self.account and name and reference:
            if Biller.objects.filter(account=self.account, name=name, reference=reference).exists():
                raise forms.ValidationError(
                    "A biller with this category and reference already exists."
                )
        return cleaned_data


class BillPaymentForm(forms.Form):
    """Pay a bill from a saved biller."""

    biller = forms.ModelChoiceField(queryset=Biller.objects.none())
    amount = forms.DecimalField(min_value=Decimal("0.01"), max_digits=12, decimal_places=2)

    def __init__(self, *args, account=None, **kwargs):
        super().__init__(*args, **kwargs)
        if account is not None:
            self.fields["biller"].queryset = account.billers.all()
