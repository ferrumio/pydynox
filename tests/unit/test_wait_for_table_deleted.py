"""Unit tests for wait_for_table_deleted and the wait option of delete_table.

The Rust waiter talks to a small local HTTP server that fakes DynamoDB, so the
polling loop runs for real without Docker or AWS credentials.
"""

from __future__ import annotations

import threading
import time
from unittest.mock import AsyncMock, MagicMock

import pytest
from pydynox import DynamoDBClient
from pydynox.exceptions import AccessDeniedException
from pydynox.testing import MemoryBackend

_EXISTS = {"Table": {"TableName": "users", "TableStatus": "DELETING"}}
_DELETED = {"TableDescription": {"TableName": "users", "TableStatus": "DELETING"}}
_ABSENT = "ResourceNotFoundException"
_DENIED = "AccessDeniedException"


def _client(fake) -> DynamoDBClient:
    return DynamoDBClient(
        region="us-east-1",
        access_key="test",
        secret_key="test",
        endpoint_url=fake.endpoint_url,
        max_retries=0,
    )


# ========== Waiter ==========


async def test_wait_returns_when_table_already_absent(fake_dynamodb) -> None:
    # GIVEN DynamoDB says the table does not exist
    server = fake_dynamodb({"DescribeTable": [_ABSENT]})

    # WHEN waiting for the table to be deleted
    await _client(server).wait_for_table_deleted("users")

    # THEN it returns after a single check
    assert server.calls == ["DescribeTable"]


def test_sync_wait_returns_when_table_already_absent(fake_dynamodb) -> None:
    # GIVEN DynamoDB says the table does not exist
    server = fake_dynamodb({"DescribeTable": [_ABSENT]})

    # WHEN waiting for the table to be deleted
    _client(server).sync_wait_for_table_deleted("users")

    # THEN it returns after a single check
    assert server.calls == ["DescribeTable"]


async def test_wait_polls_until_table_is_absent(fake_dynamodb) -> None:
    # GIVEN the table is still there for two checks and gone on the third
    script = [_EXISTS, _EXISTS, _ABSENT]
    server = fake_dynamodb({"DescribeTable": script})

    # WHEN waiting for the table to be deleted
    await _client(server).wait_for_table_deleted("users", timeout_seconds=10)

    # THEN it checks three times and then returns
    assert server.calls == ["DescribeTable"] * 3


def test_sync_wait_polls_until_table_is_absent(fake_dynamodb) -> None:
    # GIVEN the table is still there for two checks and gone on the third
    script = [_EXISTS, _EXISTS, _ABSENT]
    server = fake_dynamodb({"DescribeTable": script})

    # WHEN waiting for the table to be deleted
    _client(server).sync_wait_for_table_deleted("users", timeout_seconds=10)

    # THEN it checks three times and then returns
    assert server.calls == ["DescribeTable"] * 3


async def test_wait_times_out_while_table_exists(fake_dynamodb) -> None:
    # GIVEN the table never goes away
    server = fake_dynamodb({"DescribeTable": [_EXISTS]})
    client = _client(server)

    # WHEN waiting with a one second timeout
    # THEN a TimeoutError names the table
    with pytest.raises(TimeoutError, match="users"):
        await client.wait_for_table_deleted("users", timeout_seconds=1)

    # AND the table was checked more than once before giving up
    assert len(server.calls) >= 2


def test_sync_wait_times_out_while_table_exists(fake_dynamodb) -> None:
    # GIVEN the table never goes away
    server = fake_dynamodb({"DescribeTable": [_EXISTS]})
    client = _client(server)

    # WHEN waiting with a one second timeout
    # THEN a TimeoutError names the table
    with pytest.raises(TimeoutError, match="users"):
        client.sync_wait_for_table_deleted("users", timeout_seconds=1)


async def test_wait_propagates_service_errors(fake_dynamodb) -> None:
    # GIVEN DynamoDB denies access instead of saying the table is gone
    server = fake_dynamodb({"DescribeTable": [_DENIED]})
    client = _client(server)

    # WHEN waiting for the table to be deleted
    # THEN the error is raised, not taken as proof of deletion
    with pytest.raises(AccessDeniedException):
        await client.wait_for_table_deleted("users")

    # AND the waiter stops at the first error
    assert server.calls == ["DescribeTable"]


def test_sync_wait_propagates_service_errors(fake_dynamodb) -> None:
    # GIVEN DynamoDB denies access instead of saying the table is gone
    server = fake_dynamodb({"DescribeTable": [_DENIED]})
    client = _client(server)

    # WHEN waiting for the table to be deleted
    # THEN the error is raised, not taken as proof of deletion
    with pytest.raises(AccessDeniedException):
        client.sync_wait_for_table_deleted("users")

    # AND the waiter stops at the first error
    assert server.calls == ["DescribeTable"]


async def test_wait_propagates_service_error_after_polling(fake_dynamodb) -> None:
    # GIVEN the table exists on the first check, then access is denied
    server = fake_dynamodb({"DescribeTable": [_EXISTS, _DENIED]})
    client = _client(server)

    # WHEN waiting for the table to be deleted
    # THEN the error is raised in the middle of polling
    with pytest.raises(AccessDeniedException):
        await client.wait_for_table_deleted("users", timeout_seconds=10)

    # AND the waiter made exactly the two checks
    assert server.calls == ["DescribeTable"] * 2


# ========== delete_table ==========


async def test_delete_table_does_not_wait_by_default(fake_dynamodb) -> None:
    # GIVEN a table that still exists after the delete request
    server = fake_dynamodb({"DeleteTable": [_DELETED], "DescribeTable": [_EXISTS]})

    # WHEN deleting without the wait option
    await _client(server).delete_table("users")

    # THEN only the delete request is sent
    assert server.calls == ["DeleteTable"]


def test_sync_delete_table_does_not_wait_by_default(fake_dynamodb) -> None:
    # GIVEN a table that still exists after the delete request
    server = fake_dynamodb({"DeleteTable": [_DELETED], "DescribeTable": [_EXISTS]})

    # WHEN deleting without the wait option
    _client(server).sync_delete_table("users")

    # THEN only the delete request is sent
    assert server.calls == ["DeleteTable"]


async def test_delete_table_wait_polls_until_absent(fake_dynamodb) -> None:
    # GIVEN the table is still there after the delete request and gone on the next check
    script = [_EXISTS, _ABSENT]
    server = fake_dynamodb({"DeleteTable": [_DELETED], "DescribeTable": script})

    # WHEN deleting with wait=True
    await _client(server).delete_table("users", wait=True, timeout_seconds=10)

    # THEN the delete is followed by checks until the table is gone
    assert server.calls == ["DeleteTable", "DescribeTable", "DescribeTable"]


def test_sync_delete_table_wait_polls_until_absent(fake_dynamodb) -> None:
    # GIVEN the table is still there after the delete request and gone on the next check
    script = [_EXISTS, _ABSENT]
    server = fake_dynamodb({"DeleteTable": [_DELETED], "DescribeTable": script})

    # WHEN deleting with wait=True
    _client(server).sync_delete_table("users", wait=True, timeout_seconds=10)

    # THEN the delete is followed by checks until the table is gone
    assert server.calls == ["DeleteTable", "DescribeTable", "DescribeTable"]


async def test_delete_table_wait_times_out(fake_dynamodb) -> None:
    # GIVEN the table never goes away after the delete request
    server = fake_dynamodb({"DeleteTable": [_DELETED], "DescribeTable": [_EXISTS]})
    client = _client(server)

    # WHEN deleting with wait=True and a one second timeout
    # THEN a TimeoutError is raised
    with pytest.raises(TimeoutError):
        await client.delete_table("users", wait=True, timeout_seconds=1)


def test_sync_delete_table_wait_times_out(fake_dynamodb) -> None:
    # GIVEN the table never goes away after the delete request
    server = fake_dynamodb({"DeleteTable": [_DELETED], "DescribeTable": [_EXISTS]})
    client = _client(server)

    # WHEN deleting with wait=True and a one second timeout
    # THEN a TimeoutError is raised
    with pytest.raises(TimeoutError):
        client.sync_delete_table("users", wait=True, timeout_seconds=1)


def test_delete_table_wait_options_are_keyword_only(fake_dynamodb) -> None:
    # GIVEN a working fake DynamoDB
    server = fake_dynamodb({"DeleteTable": [_DELETED], "DescribeTable": [_EXISTS]})
    client = _client(server)

    # WHEN passing wait as a positional argument
    # THEN Python rejects the call
    with pytest.raises(TypeError):
        client.sync_delete_table("users", True)  # type: ignore[misc]


# ========== GIL release ==========


def _ticks_while_waiting_times_out(blocking_call) -> int:
    """Count how often a second Python thread runs while the call blocks."""
    ticks = 0
    done = threading.Event()

    def tick() -> None:
        nonlocal ticks
        while not done.is_set():
            ticks += 1
            time.sleep(0.01)

    ticker = threading.Thread(target=tick)
    ticker.start()
    try:
        with pytest.raises(TimeoutError):
            blocking_call()
    finally:
        done.set()
        ticker.join()
    return ticks


def test_sync_wait_for_table_deleted_releases_the_gil(fake_dynamodb) -> None:
    # GIVEN a table that never goes away and a thread that keeps counting
    server = fake_dynamodb({"DescribeTable": [_EXISTS]})
    client = _client(server)

    # WHEN a sync wait blocks until its one second timeout
    ticks = _ticks_while_waiting_times_out(
        lambda: client.sync_wait_for_table_deleted("users", timeout_seconds=1)
    )

    # THEN the other thread kept running, so the GIL was not held
    assert ticks > 20


def test_sync_wait_for_table_active_releases_the_gil(fake_dynamodb) -> None:
    # GIVEN a table that never becomes active and a thread that keeps counting
    creating = {"Table": {"TableName": "users", "TableStatus": "CREATING"}}
    server = fake_dynamodb({"DescribeTable": [creating]})
    client = _client(server)

    # WHEN a sync wait blocks until its one second timeout
    ticks = _ticks_while_waiting_times_out(
        lambda: client.sync_wait_for_table_active("users", timeout_seconds=1)
    )

    # THEN the other thread kept running, so the GIL was not held
    assert ticks > 20


# ========== Python wrapper forwarding ==========


def _client_with_mock(inner: MagicMock) -> DynamoDBClient:
    client = DynamoDBClient.__new__(DynamoDBClient)
    client._client = inner
    return client


async def test_wrapper_forwards_async_wait_for_table_deleted() -> None:
    # GIVEN a client wrapping a mocked Rust client
    inner = MagicMock()
    inner.wait_for_table_deleted = AsyncMock()

    # WHEN waiting for deletion with a timeout
    await _client_with_mock(inner).wait_for_table_deleted("users", timeout_seconds=5)

    # THEN the Rust client gets the table name and the timeout
    inner.wait_for_table_deleted.assert_called_once_with("users", timeout_seconds=5)


def test_wrapper_forwards_sync_wait_for_table_deleted() -> None:
    # GIVEN a client wrapping a mocked Rust client
    inner = MagicMock()

    # WHEN waiting for deletion with a timeout
    _client_with_mock(inner).sync_wait_for_table_deleted("users", timeout_seconds=5)

    # THEN the Rust client gets the table name and the timeout
    inner.sync_wait_for_table_deleted.assert_called_once_with("users", timeout_seconds=5)


def test_wrapper_wait_for_table_deleted_defaults_timeout_to_none() -> None:
    # GIVEN a client wrapping a mocked Rust client
    inner = MagicMock()

    # WHEN waiting for deletion without a timeout
    _client_with_mock(inner).sync_wait_for_table_deleted("users")

    # THEN the Rust client gets timeout_seconds=None, which means its default
    inner.sync_wait_for_table_deleted.assert_called_once_with("users", timeout_seconds=None)


async def test_wrapper_forwards_async_delete_options() -> None:
    # GIVEN a client wrapping a mocked Rust client
    inner = MagicMock()
    inner.delete_table = AsyncMock()

    # WHEN deleting with wait and a timeout
    await _client_with_mock(inner).delete_table("users", wait=True, timeout_seconds=5)

    # THEN the Rust client gets both options
    inner.delete_table.assert_called_once_with("users", wait=True, timeout_seconds=5)


def test_wrapper_forwards_sync_delete_options() -> None:
    # GIVEN a client wrapping a mocked Rust client
    inner = MagicMock()

    # WHEN deleting with wait and a timeout
    _client_with_mock(inner).sync_delete_table("users", wait=True, timeout_seconds=5)

    # THEN the Rust client gets both options
    inner.sync_delete_table.assert_called_once_with("users", wait=True, timeout_seconds=5)


def test_wrapper_delete_defaults_to_no_wait() -> None:
    # GIVEN a client wrapping a mocked Rust client
    inner = MagicMock()

    # WHEN deleting without options
    _client_with_mock(inner).sync_delete_table("users")

    # THEN the Rust client is told not to wait
    inner.sync_delete_table.assert_called_once_with("users", wait=False, timeout_seconds=None)


# ========== Memory backend ==========


async def test_memory_backend_async_delete_and_wait() -> None:
    with MemoryBackend() as backend:
        # GIVEN a table in the memory backend
        backend.client.sync_create_table("users", partition_key=("pk", "S"))

        # WHEN deleting it with wait=True
        await backend.client.delete_table("users", wait=True, timeout_seconds=1)

        # THEN the table is gone at once
        assert not backend.client.sync_table_exists("users")

        # AND the waiter returns for the missing table
        await backend.client.wait_for_table_deleted("users")


def test_memory_backend_sync_delete_and_wait() -> None:
    with MemoryBackend() as backend:
        # GIVEN a table in the memory backend
        backend.client.sync_create_table("users", partition_key=("pk", "S"))

        # WHEN deleting it with wait=True
        backend.client.sync_delete_table("users", wait=True, timeout_seconds=1)

        # THEN the table is gone at once
        assert not backend.client.sync_table_exists("users")

        # AND the waiter returns for the missing table
        backend.client.sync_wait_for_table_deleted("users")


def test_memory_backend_wait_for_absent_table_succeeds() -> None:
    # Very simple test: the call only has to return, so there are no sections
    with MemoryBackend() as backend:
        backend.client.sync_wait_for_table_deleted("never_created")


async def test_memory_backend_async_wait_times_out_while_table_exists() -> None:
    with MemoryBackend() as backend:
        # GIVEN a table that still exists in the memory backend
        backend.client.sync_create_table("users", partition_key=("pk", "S"))

        # WHEN waiting for its deletion with a zero timeout
        # THEN a TimeoutError names the table
        with pytest.raises(TimeoutError, match="users"):
            await backend.client.wait_for_table_deleted("users", timeout_seconds=0)

        # AND the table is untouched
        assert backend.client.sync_table_exists("users")


def test_memory_backend_sync_wait_times_out_while_table_exists() -> None:
    with MemoryBackend() as backend:
        # GIVEN a table that still exists in the memory backend
        backend.client.sync_create_table("users", partition_key=("pk", "S"))

        # WHEN waiting for its deletion with a zero timeout
        # THEN a TimeoutError names the table
        with pytest.raises(TimeoutError, match="users"):
            backend.client.sync_wait_for_table_deleted("users", timeout_seconds=0)

        # AND the table is untouched
        assert backend.client.sync_table_exists("users")


async def test_memory_backend_async_wait_returns_once_table_is_deleted() -> None:
    with MemoryBackend() as backend:
        # GIVEN a table that another thread deletes shortly after the wait starts
        backend.client.sync_create_table("users", partition_key=("pk", "S"))
        deleter = threading.Timer(0.2, backend.client.sync_delete_table, args=("users",))
        deleter.start()

        # WHEN waiting for the table to be deleted
        await backend.client.wait_for_table_deleted("users", timeout_seconds=5)
        deleter.join()

        # THEN the wait ends and the table is gone
        assert not backend.client.sync_table_exists("users")


def test_memory_backend_sync_wait_returns_once_table_is_deleted() -> None:
    with MemoryBackend() as backend:
        # GIVEN a table that another thread deletes shortly after the wait starts
        backend.client.sync_create_table("users", partition_key=("pk", "S"))
        deleter = threading.Timer(0.2, backend.client.sync_delete_table, args=("users",))
        deleter.start()

        # WHEN waiting for the table to be deleted
        backend.client.sync_wait_for_table_deleted("users", timeout_seconds=5)
        deleter.join()

        # THEN the wait ends and the table is gone
        assert not backend.client.sync_table_exists("users")
