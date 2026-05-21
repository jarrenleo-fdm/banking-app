"""Pytest configuration for the banking app."""
import pytest


@pytest.fixture(autouse=True)
def enable_db_access_for_all_tests(db):
    """Allow database access in this prototype's integration-style tests."""
