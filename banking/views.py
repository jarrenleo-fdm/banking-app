"""Views for dashboard, money movement, and transaction history."""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from .forms import DepositForm, TransferForm, WithdrawForm
from .services import (
    BankingError,
    InsufficientFundsError,
    InvalidAmountError,
    deposit,
    transfer,
    withdraw,
)


def _dashboard_context(account, **overrides):
    context = {
        "account": account,
        "balance": account.balance,
        "recent_transactions": account.transactions.select_related(
            "counterparty__user"
        ).order_by("-timestamp")[:5],
        "deposit_form": DepositForm(),
        "withdraw_form": WithdrawForm(),
        "transfer_form": TransferForm(),
    }
    context.update(overrides)
    return context


@login_required
def dashboard_view(request):
    """Render the logged-in user's balance dashboard."""
    account = request.user.account
    return render(request, "banking/dashboard.html", _dashboard_context(account))


@login_required
@require_POST
def deposit_view(request):
    """Handle a deposit POST."""
    account = request.user.account
    form = DepositForm(request.POST)
    if form.is_valid():
        try:
            transaction = deposit(account, form.cleaned_data["amount"])
        except InvalidAmountError as exc:
            form.add_error("amount", str(exc))
        else:
            messages.success(request, f"Deposited ${transaction.amount} successfully.")
            return redirect("banking:dashboard")

    return render(
        request,
        "banking/dashboard.html",
        _dashboard_context(account, deposit_form=form),
        status=200,
    )


@login_required
@require_POST
def withdraw_view(request):
    """Handle a withdrawal POST."""
    account = request.user.account
    form = WithdrawForm(request.POST)
    if form.is_valid():
        try:
            transaction = withdraw(account, form.cleaned_data["amount"])
        except (InvalidAmountError, InsufficientFundsError) as exc:
            form.add_error("amount", str(exc))
        else:
            messages.success(request, f"Withdrew ${transaction.amount} successfully.")
            return redirect("banking:dashboard")

    return render(
        request,
        "banking/dashboard.html",
        _dashboard_context(account, withdraw_form=form),
        status=200,
    )


@login_required
@require_POST
def transfer_view(request):
    """Handle an internal transfer POST."""
    account = request.user.account
    form = TransferForm(request.POST)
    if form.is_valid():
        try:
            out_transaction, _ = transfer(
                account,
                form.cleaned_data["recipient_phone"],
                form.cleaned_data["amount"],
            )
        except BankingError as exc:
            form.add_error(None, str(exc))
        else:
            recipient = out_transaction.counterparty.user
            messages.success(
                request,
                f"Sent ${out_transaction.amount} to {recipient.name}.",
            )
            return redirect("banking:dashboard")

    return render(
        request,
        "banking/dashboard.html",
        _dashboard_context(account, transfer_form=form),
        status=200,
    )


@login_required
def transaction_history_view(request):
    """Render the complete transaction history for the logged-in account."""
    account = request.user.account
    transactions = account.transactions.select_related(
        "counterparty__user"
    ).order_by("-timestamp")
    return render(
        request,
        "banking/transactions.html",
        {"account": account, "transactions": transactions},
    )
