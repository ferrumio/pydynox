"""Testing utilities for pydynox.

This module provides tools for testing pydynox code without needing
DynamoDB Local, LocalStack, or moto.

Example:
    >>> from pydynox.testing import MemoryBackend
    >>>
    >>> # As context manager
    >>> with MemoryBackend():
    ...     user = User(pk="USER#1", name="John")
    ...     user.save()
    ...     assert User.get(pk="USER#1") is not None
    >>>
    >>> # As decorator
    >>> @MemoryBackend()
    ... def test_create_user():
    ...     user = User(pk="USER#1", name="John")
    ...     user.save()
    ...     assert User.get(pk="USER#1") is not None
    >>>
    >>> # As pytest fixture
    >>> import pytest
    >>> @pytest.fixture(autouse=True)
    ... def memory_db():
    ...     with MemoryBackend():
    ...         yield
"""

from pydynox.testing.memory import MemoryBackend

__all__ = ["MemoryBackend"]
