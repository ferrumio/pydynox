"""Adaptive retry for throttled operations.

The AWS SDK already retries throttling, but it retries blind: every attempt goes
out at the same rate because the SDK knows nothing about the rate limiter. These
decorators close that loop. On throttle they call ``_on_throttle()``, which drops
the limiter rate by 20%, then retry. Because the retry re-runs the whole
operation it also re-acquires capacity, so the next attempt waits on the slower
token bucket instead of hammering the table at the old rate.

Retry only happens when a rate limiter is configured. Without one there is no
rate to lower, so the error propagates immediately, as it did before.
"""

from __future__ import annotations

import asyncio
import time
from functools import wraps
from typing import TYPE_CHECKING, Any, Awaitable, Callable, TypeVar

if TYPE_CHECKING:
    from pydynox.client._typing import _MixinBase

T = TypeVar("T")

# Backoff doubles from this value up to the cap.
_INITIAL_BACKOFF_SECONDS = 0.1
_MAX_BACKOFF_SECONDS = 5.0
_MAX_ATTEMPTS = 10

__all__ = ["retry_on_throttle", "sync_retry_on_throttle"]


def _backoff_for(attempt: int) -> float:
    """Backoff for a zero-based attempt number, capped at the maximum."""
    return min(_INITIAL_BACKOFF_SECONDS * (2**attempt), _MAX_BACKOFF_SECONDS)


def retry_on_throttle(
    method: Callable[..., Awaitable[T]],
) -> Callable[..., Awaitable[T]]:
    """Retry an async operation while DynamoDB throttles it.

    Lowers the limiter rate before each retry, so later attempts run slower.
    Passes the error straight through when no rate limiter is configured.
    """

    @wraps(method)
    async def wrapper(self: _MixinBase, *args: Any, **kwargs: Any) -> T:
        from pydynox.exceptions import ProvisionedThroughputExceededException

        if self._rate_limit is None:
            return await method(self, *args, **kwargs)

        for attempt in range(_MAX_ATTEMPTS):
            try:
                return await method(self, *args, **kwargs)
            except ProvisionedThroughputExceededException:
                self._on_throttle()
                if attempt == _MAX_ATTEMPTS - 1:
                    raise
                await asyncio.sleep(_backoff_for(attempt))

        raise AssertionError("unreachable")  # pragma: no cover

    return wrapper


def sync_retry_on_throttle(method: Callable[..., T]) -> Callable[..., T]:
    """Retry a sync operation while DynamoDB throttles it.

    Sync counterpart of :func:`retry_on_throttle`.
    """

    @wraps(method)
    def wrapper(self: _MixinBase, *args: Any, **kwargs: Any) -> T:
        from pydynox.exceptions import ProvisionedThroughputExceededException

        if self._rate_limit is None:
            return method(self, *args, **kwargs)

        for attempt in range(_MAX_ATTEMPTS):
            try:
                return method(self, *args, **kwargs)
            except ProvisionedThroughputExceededException:
                self._on_throttle()
                if attempt == _MAX_ATTEMPTS - 1:
                    raise
                time.sleep(_backoff_for(attempt))

        raise AssertionError("unreachable")  # pragma: no cover

    return wrapper
