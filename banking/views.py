"""Views for dashboard, money movement, and transaction history."""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .forms import (
    BillerForm,
    BillPaymentForm,
    BusinessBillPaymentForm,
    BusinessCreateForm,
    DepositForm,
    TransferForm,
    WithdrawForm,
)
from .models import Account, Biller, Transaction
from .services import (
    BankingError,
    InsufficientFundsError,
    InvalidAmountError,
    RecipientNotFoundError,
    approve_business_pending,
    create_business_account_mock,
    create_pending_bill_payment,
    create_pending_transfer,
    create_pending_withdrawal,
    deposit,
    deposit_to_business,
    pay_bill,
    reject_business_pending,
    transfer,
    withdraw,
)


@login_required
def dashboard_view(request):
    """Render the logged-in user's balance dashboard."""
    if hasattr(request.user, "manager_profile"):
        ba = request.user.manager_profile.business_account
        context = {
            "is_manager": True,
            "business_account": ba,
            "balance": ba.balance,
            "recent_transactions": ba.transactions.order_by("-timestamp")[:5],
            "deposit_form": DepositForm(),
            "withdraw_form": WithdrawForm(),
            "transfer_form": TransferForm(),
            "bill_pay_form": BusinessBillPaymentForm(),
        }
        return render(request, "banking/dashboard.html", context)
    account = request.user.account
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
    return render(request, "banking/dashboard.html", context)


@login_required
@require_POST
def deposit_view(request):
    """Handle a deposit POST."""
    form = DepositForm(request.POST)
    if hasattr(request.user, "manager_profile"):
        ba = request.user.manager_profile.business_account
        if form.is_valid():
            try:
                deposit_to_business(ba, form.cleaned_data["amount"])
            except InvalidAmountError as exc:
                form.add_error("amount", str(exc))
            else:
                messages.success(request, f"Deposited ${form.cleaned_data['amount']} successfully.")
                return redirect("banking:dashboard")
        return render(request, "banking/dashboard.html", {
            "is_manager": True, "business_account": ba, "balance": ba.balance,
            "recent_transactions": ba.transactions.order_by("-timestamp")[:5],
            "deposit_form": form, "withdraw_form": WithdrawForm(),
            "transfer_form": TransferForm(), "bill_pay_form": BusinessBillPaymentForm(),
        }, status=200)
    account = request.user.account
    if form.is_valid():
        amount = form.cleaned_data["amount"]
        try:
            txn = deposit(account, amount)
        except InvalidAmountError as exc:
            form.add_error("amount", str(exc))
        else:
            messages.success(request, f"Deposited ${txn.amount} successfully.")
            return redirect("banking:dashboard")
    return render(request, "banking/dashboard.html", {
        "account": account, "balance": account.balance,
        "recent_transactions": account.transactions.select_related("counterparty__user").order_by("-timestamp")[:5],
        "deposit_form": form, "withdraw_form": WithdrawForm(), "transfer_form": TransferForm(),
    }, status=200)


@login_required
@require_POST
def withdraw_view(request):
    """Handle a withdrawal POST."""
    form = WithdrawForm(request.POST)
    if hasattr(request.user, "manager_profile"):
        ba = request.user.manager_profile.business_account
        if form.is_valid():
            try:
                create_pending_withdrawal(ba, form.cleaned_data["amount"])
            except (InvalidAmountError, InsufficientFundsError) as exc:
                form.add_error("amount", str(exc))
            else:
                messages.success(request, "Withdrawal submitted and awaiting authoriser approval.")
                return redirect("banking:dashboard")
        return render(request, "banking/dashboard.html", {
            "is_manager": True, "business_account": ba, "balance": ba.balance,
            "recent_transactions": ba.transactions.order_by("-timestamp")[:5],
            "deposit_form": DepositForm(), "withdraw_form": form,
            "transfer_form": TransferForm(), "bill_pay_form": BusinessBillPaymentForm(),
        }, status=200)
    account = request.user.account
    if form.is_valid():
        amount = form.cleaned_data["amount"]
        try:
            txn = withdraw(account, amount)
        except (InvalidAmountError, InsufficientFundsError) as exc:
            form.add_error("amount", str(exc))
        else:
            messages.success(request, f"Withdrew ${txn.amount} successfully.")
            return redirect("banking:dashboard")
    return render(request, "banking/dashboard.html", {
        "account": account, "balance": account.balance,
        "recent_transactions": account.transactions.select_related("counterparty__user").order_by("-timestamp")[:5],
        "deposit_form": DepositForm(), "withdraw_form": form, "transfer_form": TransferForm(),
    }, status=200)


@login_required
@require_POST
def transfer_view(request):
    """Handle an internal transfer POST."""
    form = TransferForm(request.POST)
    if hasattr(request.user, "manager_profile"):
        ba = request.user.manager_profile.business_account
        if form.is_valid():
            try:
                create_pending_transfer(ba, form.cleaned_data["amount"], form.cleaned_data["recipient_phone"])
            except RecipientNotFoundError as exc:
                form.add_error(None, str(exc))
            except InsufficientFundsError as exc:
                form.add_error("amount", str(exc))
            else:
                messages.success(request, "Transfer submitted and awaiting authoriser approval.")
                return redirect("banking:dashboard")
        return render(request, "banking/dashboard.html", {
            "is_manager": True, "business_account": ba, "balance": ba.balance,
            "recent_transactions": ba.transactions.order_by("-timestamp")[:5],
            "deposit_form": DepositForm(), "withdraw_form": WithdrawForm(),
            "transfer_form": form, "bill_pay_form": BusinessBillPaymentForm(),
        }, status=200)
    account = request.user.account
    if form.is_valid():
        amount = form.cleaned_data["amount"]
        recipient_phone = form.cleaned_data["recipient_phone"]
        try:
            out_transaction, _ = transfer(account, recipient_phone, amount, description=form.cleaned_data.get("description", ""))
        except BankingError as exc:
            form.add_error(None, str(exc))
        else:
            recipient = out_transaction.counterparty.user
            messages.success(request, f"Sent ${out_transaction.amount} to {recipient.name}.")
            return redirect("banking:dashboard")
    return render(request, "banking/dashboard.html", {
        "account": account, "balance": account.balance,
        "recent_transactions": account.transactions.select_related("counterparty__user").order_by("-timestamp")[:5],
        "deposit_form": DepositForm(), "withdraw_form": WithdrawForm(), "transfer_form": form,
    }, status=200)


@login_required
def transaction_history_view(request):
    """Render the complete transaction history for the logged-in account."""
    if hasattr(request.user, "manager_profile"):
        return redirect("banking:dashboard")
    account = request.user.account
    transactions = account.transactions.select_related(
        "counterparty__user"
    ).order_by("-timestamp")
    return render(
        request,
        "banking/transactions.html",
        {"account": account, "transactions": transactions},
    )


def _billing_context(account, **overrides):
    context = {
        "account": account,
        "billers": account.billers.order_by("name"),
        "pay_form": BillPaymentForm(account=account),
        "add_biller_form": BillerForm(account=account),
    }
    context.update(overrides)
    return context


@login_required
def billing_view(request):
    """Render the billing page — biller list plus pay and add-biller forms."""
    if hasattr(request.user, "manager_profile"):
        return redirect("banking:dashboard")
    account = request.user.account
    return render(request, "banking/billing.html", _billing_context(account))


@login_required
@require_POST
def pay_bill_view(request):
    """Handle a bill payment POST."""
    if hasattr(request.user, "manager_profile"):
        ba = request.user.manager_profile.business_account
        form = BusinessBillPaymentForm(request.POST)
        if form.is_valid():
            try:
                create_pending_bill_payment(
                    ba,
                    form.cleaned_data["amount"],
                    form.cleaned_data["category"],
                    form.cleaned_data["reference"],
                )
            except (InvalidAmountError, InsufficientFundsError) as exc:
                form.add_error("amount", str(exc))
            else:
                messages.success(request, "Bill payment submitted and awaiting authoriser approval.")
                return redirect("banking:dashboard")
        return render(request, "banking/dashboard.html", {
            "is_manager": True, "business_account": ba, "balance": ba.balance,
            "recent_transactions": ba.transactions.order_by("-timestamp")[:5],
            "deposit_form": DepositForm(), "withdraw_form": WithdrawForm(),
            "transfer_form": TransferForm(), "bill_pay_form": form,
        }, status=200)
    account = request.user.account
    form = BillPaymentForm(request.POST, account=account)
    if form.is_valid():
        biller = form.cleaned_data["biller"]
        amount = form.cleaned_data["amount"]
        try:
            txn = pay_bill(account, biller, amount)
        except InvalidAmountError as exc:
            form.add_error("amount", str(exc))
        except InsufficientFundsError as exc:
            form.add_error("amount", str(exc))
        else:
            messages.success(request, f"Paid ${txn.amount} to {txn.description}.")
            return redirect("banking:billing")
    return render(request, "banking/billing.html", _billing_context(account, pay_form=form), status=200)


@login_required
@require_POST
def add_biller_view(request):
    """Handle adding a new biller."""
    account = request.user.account
    form = BillerForm(request.POST, account=account)
    if form.is_valid():
        Biller.objects.create(
            account=account,
            name=form.cleaned_data["name"],
            reference=form.cleaned_data["reference"],
        )
        messages.success(request, f"Biller '{form.cleaned_data['name']}' added.")
        return redirect("banking:billing")

    return render(
        request,
        "banking/billing.html",
        _billing_context(account, add_biller_form=form),
        status=200,
    )


@login_required
@require_POST
def remove_biller_view(request, biller_id):
    """Handle removing a saved biller owned by the logged-in user."""
    account = request.user.account
    biller = get_object_or_404(Biller, pk=biller_id, account=account)
    name = biller.name
    biller.delete()
    messages.success(request, f"Biller '{name}' removed.")
    return redirect("banking:billing")


@login_required
def billing_history_view(request):
    """Render the bill payment history for the logged-in user."""
    account = request.user.account
    payments = account.transactions.filter(
        transaction_type=Transaction.BILL_PAYMENT
    ).order_by("-timestamp")
    return render(
        request,
        "banking/billing_history.html",
        {"account": account, "payments": payments},
    )


def create_business_account_view(request):
    """Public form that creates a BusinessAccount with manager and authoriser via mock SQL."""
    if request.method == "POST":
        form = BusinessCreateForm(request.POST)
        if form.is_valid():
            creds = create_business_account_mock(
                company_name=form.cleaned_data["company_name"],
                uen=form.cleaned_data["uen"],
                street=form.cleaned_data["street"],
                city=form.cleaned_data["city"],
                postal_code=form.cleaned_data["postal_code"],
            )
            request.session["business_created_credentials"] = creds
            return redirect(f"/business/created/?id={creds['business_account_id']}")
        return render(request, "banking/create_business_account.html", {"form": form}, status=200)
    return render(request, "banking/create_business_account.html", {"form": BusinessCreateForm()})


def business_account_created_view(request):
    """One-time credential display — pops session key; redirects if already consumed."""
    creds = request.session.pop("business_created_credentials", None)
    if creds is None:
        return redirect("banking:create_business_account")
    return render(request, "banking/business_account_created.html", {"creds": creds})


@login_required
def authoriser_queue_view(request):
    """List all pending transactions the logged-in user is authoriser for."""
    from .models import Authoriser, PendingTransaction
    if not hasattr(request.user, "authoriser_profile"):
        return HttpResponseForbidden("You are not assigned as an authoriser.")
    business_account = request.user.authoriser_profile.business_account
    pending_txns = PendingTransaction.objects.filter(
        business_account=business_account,
        status=PendingTransaction.PENDING,
    ).select_related("counterparty__user").order_by("-created_at")
    return render(
        request,
        "banking/authoriser_queue.html",
        {"pending_txns": pending_txns},
    )


@login_required
@require_POST
def approve_transaction_view(request, pending_tx_id):
    """Approve a pending transaction as the assigned authoriser."""
    from .models import PendingTransaction
    pending_tx = get_object_or_404(
        PendingTransaction, pk=pending_tx_id, status=PendingTransaction.PENDING
    )
    if pending_tx.business_account.authoriser.user != request.user:
        return HttpResponseForbidden()
    try:
        approve_business_pending(pending_tx, request.user)
        messages.success(request, "Transaction approved and executed.")
    except BankingError as exc:
        messages.error(request, str(exc))
    return redirect("banking:authoriser_queue")


@login_required
@require_POST
def reject_transaction_view(request, pending_tx_id):
    """Reject a pending transaction as the assigned authoriser."""
    from .models import PendingTransaction
    pending_tx = get_object_or_404(
        PendingTransaction, pk=pending_tx_id, status=PendingTransaction.PENDING
    )
    if pending_tx.business_account.authoriser.user != request.user:
        return HttpResponseForbidden()
    reject_business_pending(pending_tx, request.user)
    messages.success(request, "Transaction rejected.")
    return redirect("banking:authoriser_queue")
