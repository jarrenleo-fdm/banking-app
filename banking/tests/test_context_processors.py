"""Tests for banking context processors."""
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from banking.models import AccountManagerProfile, Authoriser, BusinessAccount, PendingTransaction

User = get_user_model()


def make_business():
    ba = BusinessAccount.objects.create(
        company_name="TestCo", uen="CTX_UEN",
        street="1 St", city="Singapore", postal_code="000001",
    )
    mgr = User.objects.create_user(
        username="ctx_mgr", email="ctxmgr@test.com", name="Manager",
        phone_number="80000001", password="Demo@abc123",
    )
    auth_user = User.objects.create_user(
        username="ctx_auth", email="ctxauth@test.com", name="Authoriser",
        phone_number="80000002", password="Demo@abc123",
    )
    AccountManagerProfile.objects.create(user=mgr, business_account=ba)
    Authoriser.objects.create(user=auth_user, business_account=ba)
    return ba, mgr, auth_user


def test_pending_count_for_authoriser_with_pending_transactions(client):
    ba, _, auth_user = make_business()
    PendingTransaction.objects.create(
        business_account=ba,
        transaction_type=PendingTransaction.WITHDRAWAL,
        amount=Decimal("100.00"),
        status=PendingTransaction.PENDING,
    )
    client.force_login(auth_user)
    response = client.get(reverse("banking:dashboard"))
    assert response.context["authoriser_pending_count"] == 1


def test_pending_count_for_authoriser_with_no_pending_returns_zero(client):
    ba, _, auth_user = make_business()
    client.force_login(auth_user)
    response = client.get(reverse("banking:dashboard"))
    assert response.context["authoriser_pending_count"] == 0


def test_pending_count_for_non_authoriser_returns_zero(client):
    personal = User.objects.create_user(
        username="plain_user", email="plain@test.com", name="Plain",
        phone_number="91234567", password="Demo@abc123",
    )
    client.force_login(personal)
    response = client.get(reverse("banking:dashboard"))
    assert response.context["authoriser_pending_count"] == 0


def test_pending_count_for_anonymous_user_returns_zero(client):
    response = client.get(reverse("banking:dashboard"))
    # anonymous user gets redirected to login, so check context processor returns 0 on a public page
    # We verify by checking no error occurs for authenticated users only — context processor must return 0 for anon
    from banking.context_processors import authoriser_pending_count
    from unittest.mock import Mock
    mock_request = Mock()
    mock_request.user.is_authenticated = False
    result = authoriser_pending_count(mock_request)
    assert result == {"authoriser_pending_count": 0}
