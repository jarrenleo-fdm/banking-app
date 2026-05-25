"""URL routes for banking operations."""
from django.shortcuts import redirect
from django.urls import path

from . import views

app_name = "banking"

urlpatterns = [
    path("", lambda request: redirect("banking:dashboard"), name="home"),
    path("dashboard/", views.dashboard_view, name="dashboard"),
    path("banking/deposit/", views.deposit_view, name="deposit"),
    path("banking/withdraw/", views.withdraw_view, name="withdraw"),
    path("banking/transfer/", views.transfer_view, name="transfer"),
    path("banking/transactions/", views.transaction_history_view, name="transactions"),
    path("banking/billing/", views.billing_view, name="billing"),
    path("banking/billing/pay/", views.pay_bill_view, name="pay_bill"),
    path("banking/billing/biller/add/", views.add_biller_view, name="add_biller"),
    path(
        "banking/billing/biller/<int:biller_id>/remove/",
        views.remove_biller_view,
        name="remove_biller",
    ),
    path(
        "banking/billing/history/", views.billing_history_view, name="billing_history"
    ),
    path("banking/authorise/", views.authoriser_queue_view, name="authoriser_queue"),
    path(
        "banking/authorise/<int:pending_tx_id>/approve/",
        views.approve_transaction_view,
        name="approve_transaction",
    ),
    path(
        "banking/authorise/<int:pending_tx_id>/reject/",
        views.reject_transaction_view,
        name="reject_transaction",
    ),
    path("business/create/", views.create_business_account_view, name="create_business_account"),
    path("business/created/", views.business_account_created_view, name="business_account_created"),
]
