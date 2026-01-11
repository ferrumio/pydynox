"""Pytest plugin for pydynox.

This module is auto-discovered by pytest when pydynox is installed.
It provides fixtures for testing with in-memory backend.

Usage:
    # Just use the fixture - no conftest.py needed!
    def test_user(pydynox_memory_backend):
        user = User(pk="USER#1", name="John")
        user.save()
        assert User.get(pk="USER#1") is not None

    # Or use autouse in pyproject.toml:
    # [tool.pytest.ini_options]
    # usefixtures = ["pydynox_memory_backend"]
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Iterator

import pytest

from pydynox.testing.memory import MemoryBackend

if TYPE_CHECKING:
    pass


@pytest.fixture
def pydynox_memory_backend() -> Iterator[MemoryBackend]:
    """Fixture that provides an in-memory DynamoDB backend.

    All pydynox operations will use in-memory storage instead of
    real DynamoDB. Data is isolated per test.

    Example:
        def test_create_user(pydynox_memory_backend):
            user = User(pk="USER#1", name="John")
            user.save()
            found = User.get(pk="USER#1")
            assert found.name == "John"

        def test_with_seed_data(pydynox_memory_backend):
            # Access the backend to inspect data
            user = User(pk="USER#1", name="Test")
            user.save()
            assert "users" in pydynox_memory_backend.tables
    """
    with MemoryBackend() as backend:
        yield backend


@pytest.fixture
def pydynox_memory_backend_factory() -> Iterator[type[MemoryBackend]]:
    """Factory fixture for creating MemoryBackend with custom seed data.

    Example:
        def test_with_seed(pydynox_memory_backend_factory):
            seed = {"users": [{"pk": "USER#1", "name": "Seeded"}]}
            with pydynox_memory_backend_factory(seed=seed):
                user = User.get(pk="USER#1")
                assert user.name == "Seeded"
    """
    yield MemoryBackend


@pytest.fixture
def pydynox_seed() -> dict[str, list[dict[str, Any]]]:
    """Override this fixture to provide seed data for pydynox_memory_backend_seeded.

    Example:
        # In conftest.py
        @pytest.fixture
        def pydynox_seed():
            return {
                "users": [
                    {"pk": "USER#1", "name": "Admin", "role": "admin"},
                    {"pk": "USER#2", "name": "User", "role": "user"},
                ]
            }

        # In test file
        def test_with_seed(pydynox_memory_backend_seeded):
            admin = User.get(pk="USER#1")
            assert admin.role == "admin"
    """
    return {}


@pytest.fixture
def pydynox_memory_backend_seeded(
    pydynox_seed: dict[str, list[dict[str, Any]]],
) -> Iterator[MemoryBackend]:
    """Fixture with seed data from pydynox_seed fixture.

    Override pydynox_seed in conftest.py to provide seed data.

    Example:
        # conftest.py
        @pytest.fixture
        def pydynox_seed():
            return {"users": [{"pk": "USER#1", "name": "Test"}]}

        # test_file.py
        def test_seeded(pydynox_memory_backend_seeded):
            user = User.get(pk="USER#1")
            assert user.name == "Test"
    """
    with MemoryBackend(seed=pydynox_seed) as backend:
        yield backend
