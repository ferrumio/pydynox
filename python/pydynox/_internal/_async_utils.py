"""Small awaitable helpers (e.g. async context manager entry with no I/O)."""

from __future__ import annotations

import asyncio
from typing import TypeVar

T = TypeVar("T")


async def aidentity(value: T) -> T:
    """Return *value* as a coroutine (for :meth:`__aenter__` with no I/O).

    Uses a zero-length sleep so the coroutine is a no-op I/O-wise but still
    suspends, satisfying static rules that require a real *await* in *async* bodies.
    """
    await asyncio.sleep(0)
    return value
