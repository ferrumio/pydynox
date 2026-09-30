"""Distributed leases for functions and explicit sections of work."""

from __future__ import annotations

import inspect
from asyncio import CancelledError
from functools import wraps
from types import TracebackType
from typing import Any, Callable, ParamSpec, TypeVar, cast

from pydynox import pydynox_core
from pydynox.client import DynamoDBClient
from pydynox.transaction import SyncTransaction, Transaction

P = ParamSpec("P")
R = TypeVar("R")

LockMetrics = pydynox_core.LockMetrics
__all__ = ["DistributedLock", "SyncDistributedLock", "distributed_lock", "LockMetrics"]


class _Guard:
    def __init__(
        self,
        client: DynamoDBClient,
        *,
        table: str,
        key: str,
        lease_duration: float = 30.0,
        wait_timeout: float = 35.0,
    ) -> None:
        self._client = client
        self._native = pydynox_core.NativeLease(
            client._client, table, key, lease_duration, wait_timeout
        )

    def raise_if_lost(self) -> None:
        """Raise LockLost if this guard no longer has a valid local lease.

        This local check does not make a later write atomic with ownership.
        Use check_in() to guard writes in a DynamoDB transaction.
        """
        self._native.raise_if_lost()

    def check_in(self, transaction: Transaction | SyncTransaction) -> None:
        """Add an ownership condition to a transaction using this same client.

        The transaction must commit while the guard is active. The condition
        rejects a former owner's writes after release or takeover.
        """
        if transaction._client is not self._client:
            raise ValueError("Lock and transaction must use the same client")
        transaction.condition_check(**self._native.condition_check())

    @property
    def metrics(self) -> LockMetrics:
        """Snapshot of this acquisition's requests, renewals, and capacity."""
        return self._native.metrics


class DistributedLock(_Guard):
    """Async context manager with native automatic lease renewal.

    Requires a table with a string partition key named ``key`` and no sort key.
    Guards are single-use. Contention raises LockNotAcquired; loss of ownership
    raises LockLost. A lease cannot forcibly stop application code.

    Defaults: a 30-second lease and a 35-second acquisition budget. A zero
    wait allows one bounded attempt, including network requests. Short retries
    on the same client retain observations for abandoned-lock recovery.
    """

    async def __aenter__(self) -> DistributedLock:
        try:
            await self._native.acquire()
        except CancelledError:
            self._native.cancel()
            raise
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        try:
            await self._native.release()
        except BaseException as cleanup_error:
            if exc is None:
                raise
            exc.add_note(f"Lock cleanup also failed: {cleanup_error}")


class SyncDistributedLock(_Guard):
    """Sync equivalent of DistributedLock; waiting releases the Python GIL."""

    def __enter__(self) -> SyncDistributedLock:
        self._native.sync_acquire()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        try:
            self._native.sync_release()
        except BaseException as cleanup_error:
            if exc is None:
                raise
            exc.add_note(f"Lock cleanup also failed: {cleanup_error}")


def distributed_lock(
    client: DynamoDBClient,
    *,
    table: str,
    key: str,
    lease_duration: float = 30.0,
    wait_timeout: float = 35.0,
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """Coordinate calls to a sync or async function by a resource key.

    ``key`` may contain argument names, such as ``"sync:{customer_id}"``.
    Referenced arguments must be strings. Multiple fields use length framing
    to prevent delimiter collisions. Generators are not supported.

    Signature inspection happens once at decoration. Argument binding, key
    formatting, validation, and the lease protocol run in Rust on each call.
    Renewal is automatic for the function's lifetime while ownership is valid.
    """
    if not table:
        raise ValueError("Lock table must not be empty")

    def decorate(function: Callable[P, R]) -> Callable[P, R]:
        if inspect.isgeneratorfunction(function) or inspect.isasyncgenfunction(function):
            raise TypeError("distributed_lock does not support generator functions")
        signature = inspect.signature(function)
        parameters = [
            (
                parameter.name,
                parameter.kind.value,
                parameter.default is not inspect.Parameter.empty,
                None if parameter.default is inspect.Parameter.empty else parameter.default,
            )
            for parameter in signature.parameters.values()
        ]
        template = pydynox_core.LockKeyTemplate(key, parameters, lease_duration, wait_timeout)

        if inspect.iscoroutinefunction(function):

            @wraps(function)
            async def async_wrapper(*args: P.args, **kwargs: P.kwargs) -> Any:
                resource = template.resolve(args, kwargs)
                async with DistributedLock(
                    client,
                    table=table,
                    key=resource,
                    lease_duration=lease_duration,
                    wait_timeout=wait_timeout,
                ):
                    return await function(*args, **kwargs)

            return cast(Callable[P, R], async_wrapper)

        @wraps(function)
        def sync_wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            resource = template.resolve(args, kwargs)
            with SyncDistributedLock(
                client,
                table=table,
                key=resource,
                lease_duration=lease_duration,
                wait_timeout=wait_timeout,
            ):
                return function(*args, **kwargs)

        return sync_wrapper

    return decorate
