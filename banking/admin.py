"""Admin registration for banking records."""
from django.contrib import admin

from .models import Account, Biller, Transaction


@admin.register(Biller)
class BillerAdmin(admin.ModelAdmin):
    list_display = ("name", "account", "reference", "created_at")
    readonly_fields = ("created_at",)


@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    """Account admin with read-only balance fields."""

    list_display = ("user", "balance", "created_at")
    readonly_fields = ("balance", "created_at")


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    """Immutable transaction audit trail in the admin."""

    list_display = [
        "account",
        "transaction_type",
        "amount",
        "balance_after",
        "timestamp",
        "counterparty",
    ]
    readonly_fields = [
        "account",
        "transaction_type",
        "amount",
        "balance_after",
        "counterparty",
        "timestamp",
        "description",
    ]
