"""Models for accounts and immutable transaction history."""
from decimal import Decimal

from django.conf import settings
from django.core.validators import RegexValidator
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver


class Account(models.Model):
    """One monetary account per user."""

    PERSONAL = "PERSONAL"
    BUSINESS = "BUSINESS"
    ACCOUNT_TYPES = [
        (PERSONAL, "Personal"),
        (BUSINESS, "Business"),
    ]

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
    account_type = models.CharField(
        max_length=10,
        choices=ACCOUNT_TYPES,
        default=PERSONAL,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{str(self.user.username)} account"


class BusinessProfile(models.Model):
    """Business-specific details linked to a business account."""

    account = models.OneToOneField(
        Account,
        on_delete=models.CASCADE,
        related_name="business_profile",
    )
    company_name = models.CharField(max_length=200)
    business_registration_number = models.CharField(
        max_length=20,
        unique=True,
        validators=[RegexValidator(r"^[A-Za-z0-9]{6,20}$")],
    )

    def __str__(self):
        return str(self.company_name)


class Transaction(models.Model):
    """Immutable record of a balance-changing operation."""

    DEPOSIT = "DEPOSIT"
    WITHDRAWAL = "WITHDRAWAL"
    TRANSFER_OUT = "TRANSFER_OUT"
    TRANSFER_IN = "TRANSFER_IN"
    BILL_PAYMENT = "BILL_PAYMENT"

    TRANSACTION_TYPES = [
        (DEPOSIT, "Deposit"),
        (WITHDRAWAL, "Withdrawal"),
        (TRANSFER_OUT, "Transfer Out"),
        (TRANSFER_IN, "Transfer In"),
        (BILL_PAYMENT, "Bill Payment"),
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


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_account_for_user(sender, instance, created, **kwargs):
    """Create a zero-balance account for each new user."""
    if created:
        Account.objects.create(user=instance)
