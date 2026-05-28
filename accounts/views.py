"""Views for registration and authentication."""
import logging
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth import (
    login as auth_login,
    logout as auth_logout,
    update_session_auth_hash,
)
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from banking.services import deposit

from .api_keys import create_key, revoke_key
from .forms import APIKeyCreateForm, LoginForm, RegistrationForm, UserDetailsForm
from .models import AccountAPIKey


logger = logging.getLogger(__name__)


def signup_view(request):
    """Register a new personal account user and redirect to login."""
    if request.method == "POST":
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            initial_balance = (
                form.cleaned_data.get("initial_balance") or Decimal("0.00")
            )
            if initial_balance > Decimal("0.00"):
                deposit(user.account, initial_balance)
            messages.success(request, "Account created — please log in.")
            return redirect("accounts:login")
    else:
        form = RegistrationForm()
    return render(request, "accounts/signup.html", {"form": form})


def login_view(request):
    """Authenticate a user with a generic failure message."""
    if request.method == "POST":
        form = LoginForm(request.POST)
        if form.is_valid():
            auth_login(request, form.user)
            return redirect("banking:dashboard")
    else:
        form = LoginForm()
    return render(request, "accounts/login.html", {"form": form})


@login_required
def logout_view(request):
    """End the current session."""
    if request.method == "POST":
        auth_logout(request)
        return redirect("accounts:login")
    return render(request, "accounts/logout.html")


@login_required
def profile_view(request):
    """Let the current user update profile details and credentials."""
    password_form = PasswordChangeForm(request.user)

    if request.method == "POST" and request.POST.get("form_type") == "password":
        form = UserDetailsForm(instance=request.user)
        password_form = PasswordChangeForm(request.user, request.POST)
        if password_form.is_valid():
            user = password_form.save()
            update_session_auth_hash(request, user)
            logger.info(
                "user_credentials_updated user_id=%s fields=password",
                request.user.pk,
            )
            messages.success(request, "Your password has been updated.")
            return redirect("accounts:profile")
    elif request.method == "POST":
        form = UserDetailsForm(request.POST, instance=request.user)
        if form.is_valid():
            changed_fields = [
                field
                for field in form.changed_data
                if field in {"name", "username", "email", "phone_number"}
            ]
            if changed_fields:
                with transaction.atomic():
                    user = form.save(commit=False)
                    user.save(update_fields=changed_fields)
                logger.info(
                    "user_details_updated user_id=%s fields=%s",
                    request.user.pk,
                    ",".join(changed_fields),
                )
                messages.success(request, "Your details have been updated.")
            else:
                messages.info(request, "No changes to save.")
            return redirect("accounts:profile")
    else:
        form = UserDetailsForm(instance=request.user)
    return render(
        request,
        "accounts/profile.html",
        {
            "form": form,
            "password_form": password_form,
        },
    )


@login_required
def api_keys_view(request):
    """List and create MCP API keys for the current user."""
    api_keys = AccountAPIKey.objects.filter(user=request.user)
    if request.method == "POST":
        form = APIKeyCreateForm(request.POST, user=request.user)
        if form.is_valid():
            api_key, raw_secret = create_key(
                request.user,
                form.cleaned_data["name"],
            )
            return render(
                request,
                "accounts/api_key_created.html",
                {
                    "api_key": api_key,
                    "raw_secret": raw_secret,
                },
            )
    else:
        form = APIKeyCreateForm(user=request.user)
    return render(
        request,
        "accounts/api_keys.html",
        {
            "api_keys": api_keys,
            "form": form,
        },
    )


@login_required
@require_POST
def api_key_revoke_view(request, identifier):
    """Revoke one API key owned by the current user."""
    api_key = get_object_or_404(
        AccountAPIKey,
        user=request.user,
        identifier=identifier,
    )
    if api_key.is_active:
        revoke_key(api_key, request.user)
        messages.success(request, "API key revoked.")
    else:
        messages.info(request, "API key was already revoked.")
    return redirect("accounts:api_keys")
