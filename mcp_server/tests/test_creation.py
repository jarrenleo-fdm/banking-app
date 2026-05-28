import pytest


@pytest.mark.django_db
class TestCreatePersonalAccount:
    def test_success_with_positive_initial_deposit(self):
        from accounts.models import AccountAPIKey
        from mcp_server.server import create_personal_account

        result = create_personal_account(
            name="Dana Lim",
            username="dana",
            email="dana@example.com",
            phone_number="81230001",
            password="StrongPass123!",
            initial_deposit="500.00",
        )

        assert result["username"] == "dana"
        assert result["name"] == "Dana Lim"
        assert result["phone_number"] == "81230001"
        assert result["balance"] == "500.00"
        assert "created_at" in result
        assert "api_key" not in result
        assert AccountAPIKey.objects.count() == 0

    def test_success_with_explicit_zero_initial_balance(self):
        from django.contrib.auth import get_user_model
        from mcp_server.server import create_personal_account

        result = create_personal_account(
            "Evan Tan",
            "evan",
            "evan@example.com",
            "81230002",
            "StrongPass123!",
            "0.00",
        )

        user = get_user_model().objects.get(username="evan")
        assert result["balance"] == "0.00"
        assert user.account.transactions.count() == 0

    def test_success_with_omitted_initial_balance(self):
        from mcp_server.server import create_personal_account

        result = create_personal_account(
            "Faye Ong",
            "faye",
            "faye@example.com",
            "81230003",
            "StrongPass123!",
        )

        assert result["balance"] == "0.00"

    def test_duplicate_username_returns_error(self, db_user):
        from mcp_server.server import create_personal_account

        result = create_personal_account(
            "Alice Other",
            "ALICE",
            "alice2@example.com",
            "81230004",
            "StrongPass123!",
        )

        assert result == {"error": "Username is already taken."}

    def test_duplicate_email_returns_error(self, db_user):
        from mcp_server.server import create_personal_account

        result = create_personal_account(
            "New Alice",
            "newalice",
            "alice@example.com",
            "81230004",
            "StrongPass123!",
        )

        assert result == {"error": "Email is already registered."}

    def test_duplicate_phone_returns_error(self, db_user):
        from mcp_server.server import create_personal_account

        result = create_personal_account(
            "New Alice",
            "newalice",
            "newalice@example.com",
            "81234567",
            "StrongPass123!",
        )

        assert result == {"error": "Phone number is already registered."}

    def test_invalid_phone_returns_error(self):
        from mcp_server.server import create_personal_account

        result = create_personal_account(
            "Bad Phone",
            "badphone",
            "badphone@example.com",
            "71234567",
            "StrongPass123!",
        )

        assert result == {"error": "Enter a valid Singapore mobile number."}

    def test_weak_password_returns_error(self):
        from mcp_server.server import create_personal_account

        result = create_personal_account(
            "Weak Password",
            "weakpass",
            "weakpass@example.com",
            "81230005",
            "weak",
        )

        assert "error" in result
        assert "password" in result["error"].lower()

    def test_negative_initial_balance_returns_error_without_creating_user(self):
        from django.contrib.auth import get_user_model
        from mcp_server.server import create_personal_account

        result = create_personal_account(
            "Negative Balance",
            "negative",
            "negative@example.com",
            "81230006",
            "StrongPass123!",
            "-1.00",
        )

        assert result == {"error": "Amount must be greater than or equal to zero."}
        assert not get_user_model().objects.filter(username="negative").exists()

    def test_non_numeric_initial_balance_returns_error(self):
        from mcp_server.server import create_personal_account

        result = create_personal_account(
            "Bad Amount",
            "badamount",
            "badamount@example.com",
            "81230007",
            "StrongPass123!",
            "abc",
        )

        assert result == {"error": "Invalid amount."}

    def test_over_precise_initial_balance_returns_error(self):
        from mcp_server.server import create_personal_account

        result = create_personal_account(
            "Precise Amount",
            "precise",
            "precise@example.com",
            "81230008",
            "StrongPass123!",
            "1.001",
        )

        assert result == {"error": "Amount must have at most 2 decimal places."}
