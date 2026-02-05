"""Integration tests for logging functionality."""

from __future__ import annotations

import logging

import pytest
from pydynox import set_correlation_id, set_logger
from pydynox._internal._logging import get_logger


@pytest.fixture
def capture_logs(caplog):
    """Capture pydynox logs at INFO level."""
    caplog.set_level(logging.INFO, logger="pydynox")
    return caplog


@pytest.mark.asyncio
async def test_put_item_logs_operation(dynamo, capture_logs):
    """put_item logs the operation."""
    # WHEN we put an item
    await dynamo.put_item("test_table", {"pk": "USER#1", "sk": "PROFILE", "name": "John"})

    # THEN the operation is logged
    assert len(capture_logs.records) >= 1
    msg = capture_logs.records[0].message
    assert "put_item" in msg
    assert "table=test_table" in msg
    assert "duration_ms=" in msg


@pytest.mark.asyncio
async def test_get_item_logs_operation(dynamo, capture_logs):
    """get_item logs the operation."""
    await dynamo.put_item("test_table", {"pk": "USER#1", "sk": "PROFILE"})
    capture_logs.clear()

    await dynamo.get_item("test_table", {"pk": "USER#1", "sk": "PROFILE"})

    assert len(capture_logs.records) >= 1
    msg = capture_logs.records[0].message
    assert "get_item" in msg
    assert "table=test_table" in msg


@pytest.mark.asyncio
async def test_delete_item_logs_operation(dynamo, capture_logs):
    """delete_item logs the operation."""
    await dynamo.put_item("test_table", {"pk": "USER#1", "sk": "PROFILE"})
    capture_logs.clear()

    await dynamo.delete_item("test_table", {"pk": "USER#1", "sk": "PROFILE"})

    assert len(capture_logs.records) >= 1
    msg = capture_logs.records[0].message
    assert "delete_item" in msg


@pytest.mark.asyncio
async def test_update_item_logs_operation(dynamo, capture_logs):
    """update_item logs the operation."""
    await dynamo.put_item("test_table", {"pk": "USER#1", "sk": "PROFILE", "count": 0})
    capture_logs.clear()

    await dynamo.update_item("test_table", {"pk": "USER#1", "sk": "PROFILE"}, updates={"count": 5})

    assert len(capture_logs.records) >= 1
    msg = capture_logs.records[0].message
    assert "update_item" in msg


@pytest.mark.asyncio
async def test_query_logs_operation(dynamo, capture_logs):
    """query logs the operation."""
    for i in range(3):
        await dynamo.put_item("test_table", {"pk": "ORG#1", "sk": f"USER#{i}"})
    capture_logs.clear()

    result = dynamo.query(
        "test_table",
        key_condition_expression="#pk = :pk",
        expression_attribute_names={"#pk": "pk"},
        expression_attribute_values={":pk": "ORG#1"},
    )
    _ = [item async for item in result]  # Trigger fetch

    assert len(capture_logs.records) >= 1
    msg = capture_logs.records[0].message
    assert "query" in msg
    assert "table=test_table" in msg
    assert "items=" in msg


@pytest.mark.asyncio
async def test_correlation_id_in_logs(dynamo, capture_logs):
    """Correlation ID appears in logs when set."""
    # GIVEN a correlation ID is set
    set_correlation_id("lambda-req-123")

    # WHEN we do an operation
    await dynamo.put_item("test_table", {"pk": "USER#1", "sk": "PROFILE"})

    # THEN the correlation ID is in the log record
    record = capture_logs.records[0]
    assert hasattr(record, "correlation_id") or "correlation_id" in getattr(record, "__dict__", {})

    # Cleanup
    set_correlation_id(None)


class MockLogger:
    """Mock logger for testing custom logger."""

    def __init__(self):
        self.messages: list[tuple[str, str]] = []

    def info(self, msg: str, **kwargs):
        self.messages.append(("info", msg))

    def debug(self, msg: str, **kwargs):
        self.messages.append(("debug", msg))

    def warning(self, msg: str, **kwargs):
        self.messages.append(("warning", msg))

    def error(self, msg: str, **kwargs):
        self.messages.append(("error", msg))


@pytest.mark.asyncio
async def test_custom_logger_receives_operation_logs(dynamo):
    """Custom logger receives logs from operations."""
    original = get_logger()
    mock = MockLogger()
    set_logger(mock)

    await dynamo.put_item("test_table", {"pk": "USER#1", "sk": "PROFILE"})

    assert len(mock.messages) >= 1
    # Find the INFO level message (debug logs come first)
    info_msgs = [(level, msg) for level, msg in mock.messages if level == "info"]
    assert len(info_msgs) >= 1
    level, msg = info_msgs[0]
    assert "put_item" in msg

    # Restore
    set_logger(original)


@pytest.mark.asyncio
async def test_set_logger_with_sdk_debug(dynamo):
    """set_logger with sdk_debug=True enables SDK debug logs."""
    original = get_logger()
    mock = MockLogger()

    # Enable SDK debug - should not raise
    set_logger(mock, sdk_debug=True)

    # Operations should still work
    await dynamo.put_item("test_table", {"pk": "USER#1", "sk": "PROFILE"})

    assert len(mock.messages) >= 1

    # Restore
    set_logger(original)
