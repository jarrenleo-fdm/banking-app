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
]
