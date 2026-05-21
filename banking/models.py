"""Models for accounts and immutable transaction history."""
from decimal import Decimal

from django.conf import settings
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver


class Account(models.Model):
    """One monetary account per user."""

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


class Transaction(models.Model):
    """Immutable record of a balance-changing operation."""

    DEPOSIT = "DEPOSIT"
    WITHDRAWAL = "WITHDRAWAL"
    TRANSFER_OUT = "TRANSFER_OUT"
    TRANSFER_IN = "TRANSFER_IN"

    TRANSACTION_TYPES = [
        (DEPOSIT, "Deposit"),
        (WITHDRAWAL, "Withdrawal"),
        (TRANSFER_OUT, "Transfer Out"),
        (TRANSFER_IN, "Transfer In"),
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


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_account_for_user(sender, instance, created, **kwargs):
    """Create a zero-balance account for each new user."""
    if created:
        Account.objects.create(user=instance)
