"""Views for registration and authentication."""
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth import login as auth_login
from django.contrib.auth import logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from banking.services import deposit

from .forms import LoginForm, RegistrationForm


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
