"""Template tests for the light/dark mode theme toggle (spec 005)."""
import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

User = get_user_model()


def create_user():
    return User.objects.create_user(
        username="ThemeUser",
        email="theme@example.com",
        name="Theme User",
        phone_number="81234567",
        password="StrongerPass123",
    )


# ── T004: toggle button present in every authenticated view ──────────────────

@pytest.mark.parametrize("url_name", [
    "banking:dashboard",
    "banking:transactions",
    "banking:billing",
    "banking:billing_history",
])
def test_toggle_button_present_in_authenticated_views(client, url_name):
    user = create_user()
    client.force_login(user)

    response = client.get(reverse(url_name))

    assert response.status_code == 200
    assert b'id="theme-toggle"' in response.content


# ── T005: toggle button present in every auth view ───────────────────────────

@pytest.mark.parametrize("url_name", [
    "accounts:login",
    "accounts:signup",
    "accounts:password_reset",
    "accounts:password_reset_done",
])
def test_toggle_button_present_in_auth_views(client, url_name):
    response = client.get(reverse(url_name))

    assert response.status_code == 200
    assert b'id="theme-toggle"' in response.content


# ── FR-005: toggle button must contain both icon elements ───────────────────

@pytest.mark.parametrize("url_name,authenticated", [
    ("banking:dashboard", True),
    ("banking:transactions", True),
    ("banking:billing", True),
    ("banking:billing_history", True),
    ("accounts:login", False),
    ("accounts:signup", False),
    ("accounts:password_reset", False),
    ("accounts:password_reset_done", False),
])
def test_toggle_button_contains_both_icons(client, url_name, authenticated):
    if authenticated:
        user = create_user()
        client.force_login(user)

    response = client.get(reverse(url_name))

    assert response.status_code == 200
    assert b'class="icon-sun"' in response.content
    assert b'class="icon-moon"' in response.content


# ── T009: <html> must NOT carry a hardcoded data-theme attribute ──────────────

@pytest.mark.parametrize("url_name,authenticated", [
    ("banking:dashboard", True),
    ("banking:transactions", True),
    ("banking:billing", True),
    ("banking:billing_history", True),
    ("accounts:login", False),
    ("accounts:signup", False),
    ("accounts:password_reset", False),
    ("accounts:password_reset_done", False),
])
def test_html_element_has_no_hardcoded_data_theme(client, url_name, authenticated):
    if authenticated:
        user = create_user()
        client.force_login(user)

    response = client.get(reverse(url_name))

    assert response.status_code == 200
    assert b'<html data-theme=' not in response.content
    assert b'<html lang="en" data-theme=' not in response.content
