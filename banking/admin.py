"""Admin registration for banking records."""
from django.contrib import admin

from .models import (
    Account,
    AccountManagerProfile,
    Authoriser,
    Biller,
    BusinessAccount,
    BusinessTransaction,
    PendingTransaction,
    Transaction,
)


@admin.register(Biller)
class BillerAdmin(admin.ModelAdmin):
    list_display = ("name", "account", "reference", "created_at")
    readonly_fields = ("created_at",)


@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ("user", "balance", "created_at")
    readonly_fields = ("balance", "created_at")


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
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


@admin.register(BusinessAccount)
class BusinessAccountAdmin(admin.ModelAdmin):
    list_display = ("company_name", "uen", "balance", "created_at")
    readonly_fields = ("balance", "created_at")


@admin.register(AccountManagerProfile)
class AccountManagerProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "business_account")


@admin.register(BusinessTransaction)
class BusinessTransactionAdmin(admin.ModelAdmin):
    list_display = [
        "business_account",
        "transaction_type",
        "amount",
        "balance_after",
        "timestamp",
    ]
    readonly_fields = [
        "business_account",
        "transaction_type",
        "amount",
        "balance_after",
        "counterparty",
        "description",
        "timestamp",
    ]


@admin.register(Authoriser)
class AuthoriserAdmin(admin.ModelAdmin):
    list_display = ["business_account", "user", "assigned_at"]
    readonly_fields = ["assigned_at"]


@admin.register(PendingTransaction)
class PendingTransactionAdmin(admin.ModelAdmin):
    list_display = [
        "business_account", "transaction_type", "amount", "status", "created_at", "decided_by"
    ]
    readonly_fields = ["created_at", "decided_at"]
