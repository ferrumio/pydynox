"""Shared fixtures for unit tests.

Unit tests should NOT use moto server or real DynamoDB.
They use mocks instead.
"""

import pytest
from pydynox import clear_default_client


@pytest.fixture(autouse=True)
def reset_default_client():
    """Reset default client before and after each test."""
    clear_default_client()
    yield
    clear_default_client()
