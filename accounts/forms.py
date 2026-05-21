"""Forms for registration and login."""
from decimal import Decimal

from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator

from banking.models import BusinessProfile


User = get_user_model()

ACCOUNT_TYPE_CHOICES = [
    ("PERSONAL", "Personal"),
    ("BUSINESS", "Business"),
]


class RegistrationForm(forms.ModelForm):
    """Registration form for the custom user model."""

    password1 = forms.CharField(
        label="Password",
        widget=forms.PasswordInput,
        strip=False,
    )
    password2 = forms.CharField(
        label="Confirm password",
        widget=forms.PasswordInput,
        strip=False,
    )
    initial_balance = forms.DecimalField(
        label="Initial balance (optional)",
        min_value=Decimal("0.00"),
        max_digits=12,
        decimal_places=2,
        required=False,
        initial=Decimal("0.00"),
    )
    account_type = forms.ChoiceField(
        label="Account type",
        choices=ACCOUNT_TYPE_CHOICES,
        initial="PERSONAL",
        required=False,
    )
    company_name = forms.CharField(
        label="Company name",
        max_length=200,
        required=False,
    )
    business_registration_number = forms.CharField(
        label="Business registration number",
        max_length=20,
        required=False,
        validators=[RegexValidator(
            r"^[A-Za-z0-9]{6,20}$",
            "Enter a valid registration number (6–20 alphanumeric characters).",
        )],
    )

    class Meta:
        model = User
        fields = ["name", "username", "email", "phone_number"]

    def clean_username(self):
        username = self.cleaned_data["username"].strip()
        if User.objects.filter(username__iexact=username).exists():
            raise ValidationError("Username is already taken.")
        return username

    def clean_email(self):
        email = self.cleaned_data["email"].lower()
        if User.objects.filter(email=email).exists():
            raise ValidationError("Email is already registered.")
        return email

    def clean_phone_number(self):
        phone_number = (
            self.cleaned_data["phone_number"].replace(" ", "").replace("-", "")
        )
        if User.objects.filter(phone_number=phone_number).exists():
            raise ValidationError("Phone number is already registered.")
        return phone_number

    def clean(self):
        cleaned = super().clean()
        password1 = cleaned.get("password1")
        password2 = cleaned.get("password2")
        if password1 and password2 and password1 != password2:
            self.add_error("password2", "Passwords do not match.")
        if password1:
            validate_password(password1)

        if not cleaned.get("account_type"):
            cleaned["account_type"] = "PERSONAL"

        if cleaned.get("account_type") == "BUSINESS":
            company_name = cleaned.get("company_name", "").strip()
            reg_number = cleaned.get("business_registration_number", "").strip()
            if not company_name:
                self.add_error(
                    "company_name",
                    "Company name is required for business accounts.",
                )
            if not reg_number:
                self.add_error(
                    "business_registration_number",
                    "Business registration number is required for business accounts.",
                )
            elif BusinessProfile.objects.filter(
                business_registration_number=reg_number
            ).exists():
                self.add_error(
                    "business_registration_number",
                    "This registration number is already in use.",
                )
        return cleaned

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
        return user


class LoginForm(forms.Form):
    """Login form that never reveals which credential failed."""

    username = forms.CharField(max_length=150)
    password = forms.CharField(widget=forms.PasswordInput, strip=False)
    user = None

    def clean(self):
        cleaned = super().clean()
        username = cleaned.get("username")
        password = cleaned.get("password")
        if not username or not password:
            return cleaned

        try:
            user = User.objects.get(username__iexact=username)
        except User.DoesNotExist as exc:
            raise ValidationError("Invalid username or password.") from exc

        if not user.check_password(password) or not user.is_active:
            raise ValidationError("Invalid username or password.")

        self.user = user
        return cleaned
