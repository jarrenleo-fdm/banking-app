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
            dup = Biller.objects.filter(
                account=self.account, name=name, reference=reference
            ).exists()
            if dup:
                raise forms.ValidationError(
                    "A biller with this category and reference already exists."
                )
        return cleaned_data


class BillPaymentForm(forms.Form):
    """Pay a bill from a saved biller."""

    biller = forms.ModelChoiceField(queryset=Biller.objects.none())
    amount = forms.DecimalField(
        min_value=Decimal("0.01"), max_digits=12, decimal_places=2
    )

    def __init__(self, *args, account=None, **kwargs):
        super().__init__(*args, **kwargs)
        if account is not None:
            self.fields["biller"].queryset = account.billers.all()


class BusinessCreateForm(forms.Form):
    """Form for creating a business account."""

    company_name = forms.CharField(max_length=200)
    uen = forms.CharField(max_length=50)
    street = forms.CharField(max_length=200)
    city = forms.CharField(max_length=100)
    postal_code = forms.CharField(max_length=20)
    initial_deposit = forms.DecimalField(
        min_value=Decimal("7000.00"), max_digits=12, decimal_places=2, label="Initial Deposit"
    )

    def clean_company_name(self):
        value = self.cleaned_data["company_name"].strip()
        if not value:
            raise forms.ValidationError("This field is required.")
        return value

    def clean_uen(self):
        value = self.cleaned_data["uen"].strip()
        if not value:
            raise forms.ValidationError("This field is required.")
        from .models import BusinessAccount
        if BusinessAccount.objects.filter(uen=value).exists():
            raise forms.ValidationError("A business account with this UEN already exists.")
        return value

    def clean_street(self):
        value = self.cleaned_data["street"].strip()
        if not value:
            raise forms.ValidationError("This field is required.")
        return value

    def clean_city(self):
        value = self.cleaned_data["city"].strip()
        if not value:
            raise forms.ValidationError("This field is required.")
        return value

    def clean_postal_code(self):
        value = self.cleaned_data["postal_code"].strip()
        if not value:
            raise forms.ValidationError("This field is required.")
        return value


class BusinessBillPaymentForm(forms.Form):
    """Inline bill payment form for business accounts."""

    CATEGORY_CHOICES = [
        ("utilities", "Utilities"),
        ("telecommunications", "Telecommunications"),
        ("insurance", "Insurance"),
        ("rent", "Rent"),
        ("other", "Other"),
    ]

    category = forms.ChoiceField(choices=CATEGORY_CHOICES)
    reference = forms.CharField(max_length=100)
    amount = forms.DecimalField(
        min_value=Decimal("0.01"), max_digits=12, decimal_places=2
    )
