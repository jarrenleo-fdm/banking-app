"""Forms for registration and login."""
import re
from decimal import Decimal

from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.core.exceptions import ValidationError

from .models import AccountAPIKey


User = get_user_model()
USERNAME_VALIDATOR = UnicodeUsernameValidator()


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

    class Meta:
        model = User
        fields = ["name", "username", "email", "phone_number"]

    def clean_username(self):
        username = self.cleaned_data["username"].strip()
        USERNAME_VALIDATOR(username)
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


class UserDetailsForm(forms.ModelForm):
    """Allow a signed-in user to update profile details."""

    username = forms.CharField(
        label="Username",
        max_length=150,
        validators=[USERNAME_VALIDATOR],
    )
    phone_number = forms.CharField(max_length=10)

    class Meta:
        model = User
        fields = ["name", "username", "email", "phone_number"]

    def clean_name(self):
        name = self.cleaned_data["name"].strip()
        if not name:
            raise ValidationError("Name is required.")
        return name

    def clean_username(self):
        username = self.cleaned_data["username"].strip()
        if not username:
            raise ValidationError("Username is required.")
        duplicate = User.objects.filter(username__iexact=username).exclude(
            pk=self.instance.pk
        )
        if duplicate.exists():
            raise ValidationError("Username is already taken.")
        return username

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        duplicate = User.objects.filter(email=email).exclude(
            pk=self.instance.pk
        )
        if duplicate.exists():
            raise ValidationError("Email is already registered.")
        return email

    def clean_phone_number(self):
        phone_number = (
            self.cleaned_data["phone_number"].strip().replace(" ", "").replace("-", "")
        )
        if not re.fullmatch(r"^[89]\d{7}$", phone_number):
            raise ValidationError("Enter an 8 digit phone number starting with 8 or 9.")
        duplicate = User.objects.filter(phone_number=phone_number).exclude(
            pk=self.instance.pk
        )
        if duplicate.exists():
            raise ValidationError("Phone number is already registered.")
        return phone_number


class APIKeyCreateForm(forms.Form):
    """Create an MCP API key after confirming the user's password."""

    name = forms.CharField(max_length=80)
    password = forms.CharField(widget=forms.PasswordInput, strip=False)

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

    def clean_name(self):
        name = self.cleaned_data["name"].strip()
        if not name:
            raise ValidationError("Name is required.")
        duplicate = AccountAPIKey.objects.filter(
            user=self.user,
            name__iexact=name,
            revoked_at__isnull=True,
        )
        if duplicate.exists():
            raise ValidationError("An active API key with this name already exists.")
        return name

    def clean_password(self):
        password = self.cleaned_data["password"]
        if not self.user or not self.user.check_password(password):
            raise ValidationError("Could not confirm your identity.")
        return password

    def clean(self):
        cleaned = super().clean()
        if (
            self.user
            and AccountAPIKey.active_count_for_user(self.user)
            >= AccountAPIKey.ACTIVE_KEY_LIMIT
        ):
            limit = AccountAPIKey.ACTIVE_KEY_LIMIT
            raise ValidationError(
                f"You can have at most {limit} active API keys."
            )
        return cleaned
