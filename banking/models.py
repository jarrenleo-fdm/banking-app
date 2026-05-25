"""Models for accounts and immutable transaction history."""
from decimal import Decimal

from django.conf import settings
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver


class Account(models.Model):
    """One monetary account per user (personal only)."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="account",
    )
    balance = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{str(self.user.username)} account"


class BusinessAccount(models.Model):
    """Standalone banking entity representing a business. Not a login account."""

    company_name = models.CharField(max_length=200)
    uen = models.CharField(max_length=50, unique=True)
    street = models.CharField(max_length=200)
    city = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=20)
    balance = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return str(self.company_name)


class AccountManagerProfile(models.Model):
    """Links a CustomUser 1:1 to a BusinessAccount as its account manager."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="manager_profile",
    )
    business_account = models.OneToOneField(
        BusinessAccount,
        on_delete=models.CASCADE,
        related_name="manager",
    )

    def __str__(self):
        return f"Manager of {self.business_account}"


class Transaction(models.Model):
    """Immutable record of a balance-changing operation on a personal Account."""

    DEPOSIT = "DEPOSIT"
    WITHDRAWAL = "WITHDRAWAL"
    TRANSFER_OUT = "TRANSFER_OUT"
    TRANSFER_IN = "TRANSFER_IN"
    BILL_PAYMENT = "BILL_PAYMENT"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"

    TRANSACTION_TYPES = [
        (DEPOSIT, "Deposit"),
        (WITHDRAWAL, "Withdrawal"),
        (TRANSFER_OUT, "Transfer Out"),
        (TRANSFER_IN, "Transfer In"),
        (BILL_PAYMENT, "Bill Payment"),
        (REJECTED, "Rejected"),
        (CANCELLED, "Cancelled"),
    ]

    account = models.ForeignKey(
        Account,
        on_delete=models.PROTECT,
        related_name="transactions",
    )
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    balance_after = models.DecimalField(max_digits=12, decimal_places=2)
    counterparty = models.ForeignKey(
        Account,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="counterparty_transactions",
    )
    timestamp = models.DateTimeField(auto_now_add=True)
    description = models.CharField(max_length=200, blank=True)

    class Meta:
        ordering = ["-timestamp"]

    def __str__(self):
        return f"{self.get_transaction_type_display()} {self.amount}"


class BusinessTransaction(models.Model):
    """Immutable record of an executed or rejected transaction on a BusinessAccount."""

    DEPOSIT = "DEPOSIT"
    WITHDRAWAL = "WITHDRAWAL"
    TRANSFER_OUT = "TRANSFER_OUT"
    BILL_PAYMENT = "BILL_PAYMENT"
    REJECTED = "REJECTED"

    TRANSACTION_TYPES = [
        (DEPOSIT, "Deposit"),
        (WITHDRAWAL, "Withdrawal"),
        (TRANSFER_OUT, "Transfer Out"),
        (BILL_PAYMENT, "Bill Payment"),
        (REJECTED, "Rejected"),
    ]

    business_account = models.ForeignKey(
        BusinessAccount,
        on_delete=models.PROTECT,
        related_name="transactions",
    )
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    balance_after = models.DecimalField(max_digits=12, decimal_places=2)
    counterparty = models.ForeignKey(
        Account,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="counterparty_business_transactions",
    )
    description = models.CharField(max_length=200, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-timestamp"]

    def __str__(self):
        return f"{self.get_transaction_type_display()} {self.amount}"


class Biller(models.Model):
    """A named payee saved by a user for repeated bill payments."""

    ELECTRICITY = "ELECTRICITY"
    WATER_UTILITIES = "WATER_UTILITIES"
    INTERNET_BROADBAND = "INTERNET_BROADBAND"
    TELECOMMUNICATIONS = "TELECOMMUNICATIONS"
    TOWN_COUNCIL = "TOWN_COUNCIL"

    BILLER_CATEGORIES = [
        (ELECTRICITY, "Electricity"),
        (WATER_UTILITIES, "Water & Utilities"),
        (INTERNET_BROADBAND, "Internet & Broadband"),
        (TELECOMMUNICATIONS, "Telecommunications"),
        (TOWN_COUNCIL, "Town Council / Maintenance"),
    ]

    account = models.ForeignKey(
        Account,
        on_delete=models.CASCADE,
        related_name="billers",
    )
    name = models.CharField(max_length=50, choices=BILLER_CATEGORIES)
    reference = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("account", "name", "reference")]

    def __str__(self):
        return f"{self.get_name_display()} ({self.reference})"


class Authoriser(models.Model):
    """Assigned approver for a business account's pending transactions (1:1 per business)."""

    business_account = models.OneToOneField(
        BusinessAccount,
        on_delete=models.CASCADE,
        related_name="authoriser",
    )
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="authoriser_profile",
    )
    assigned_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Authoriser for {self.business_account}"


class PendingTransaction(models.Model):
    """Queued outgoing transaction awaiting authoriser approval for a BusinessAccount."""

    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"

    STATUS_CHOICES = [
        (PENDING, "Pending"),
        (APPROVED, "Approved"),
        (REJECTED, "Rejected"),
        (CANCELLED, "Cancelled"),
    ]

    WITHDRAWAL = "WITHDRAWAL"
    TRANSFER_OUT = "TRANSFER_OUT"
    BILL_PAYMENT = "BILL_PAYMENT"

    TRANSACTION_TYPE_CHOICES = [
        (WITHDRAWAL, "Withdrawal"),
        (TRANSFER_OUT, "Transfer Out"),
        (BILL_PAYMENT, "Bill Payment"),
    ]

    business_account = models.ForeignKey(
        BusinessAccount,
        on_delete=models.PROTECT,
        related_name="pending_transactions",
    )
    transaction_type = models.CharField(
        max_length=20,
        choices=TRANSACTION_TYPE_CHOICES,
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    counterparty = models.ForeignKey(
        Account,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="incoming_pending_transactions",
    )
    description = models.CharField(max_length=200, blank=True)
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default=PENDING,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    decided_at = models.DateTimeField(null=True, blank=True)
    decided_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="transaction_decisions",
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.get_transaction_type_display()} {self.amount} [{self.status}]"


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_account_for_user(sender, instance, created, **kwargs):
    """Create a zero-balance account for each new user."""
    if created:
        Account.objects.create(user=instance)
