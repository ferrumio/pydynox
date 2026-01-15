"""Tests for hot partition detection."""

import logging
from unittest.mock import patch

import pytest
from pydynox import DynamoDBClient, clear_default_client
from pydynox.diagnostics import HotPartitionDetector


@pytest.fixture(autouse=True)
def reset_state():
    """Reset default client before and after each test."""
    clear_default_client()
    yield
    clear_default_client()


def test_hot_partition_detector_creation():
    """HotPartitionDetector can be created with thresholds."""
    # WHEN we create a detector with custom thresholds
    detector = HotPartitionDetector(
        writes_threshold=100,
        reads_threshold=300,
        window_seconds=30,
    )

    # THEN thresholds should be set correctly
    assert detector.writes_threshold == 100
    assert detector.reads_threshold == 300
    assert detector.window_seconds == 30


def test_record_write_tracks_count():
    """record_write tracks write count per partition."""
    # GIVEN a detector
    detector = HotPartitionDetector(
        writes_threshold=100,
        reads_threshold=300,
        window_seconds=60,
    )

    # WHEN we record writes for a partition
    for _ in range(5):
        detector.record_write("users", "USER#1")

    # THEN write count should be tracked
    assert detector.get_write_count("users", "USER#1") == 5
    assert detector.get_write_count("users", "USER#2") == 0


def test_record_read_tracks_count():
    """record_read tracks read count per partition."""
    # GIVEN a detector
    detector = HotPartitionDetector(
        writes_threshold=100,
        reads_threshold=300,
        window_seconds=60,
    )

    # WHEN we record reads for a partition
    for _ in range(10):
        detector.record_read("orders", "ORDER#1")

    # THEN read count should be tracked
    assert detector.get_read_count("orders", "ORDER#1") == 10


def test_separate_tables_tracked_separately():
    """Different tables are tracked separately."""
    # GIVEN a detector
    detector = HotPartitionDetector(
        writes_threshold=100,
        reads_threshold=300,
        window_seconds=60,
    )

    # WHEN we record writes for same PK in different tables
    for _ in range(3):
        detector.record_write("users", "PK#1")
        detector.record_write("orders", "PK#1")

    # THEN each table should have its own count
    assert detector.get_write_count("users", "PK#1") == 3
    assert detector.get_write_count("orders", "PK#1") == 3


def test_logs_warning_when_threshold_exceeded(caplog):
    """Logs warning when write threshold is exceeded."""
    # GIVEN a detector with low threshold
    detector = HotPartitionDetector(
        writes_threshold=5,
        reads_threshold=10,
        window_seconds=60,
    )

    # WHEN we exceed the write threshold
    with caplog.at_level(logging.WARNING, logger="pydynox.diagnostics"):
        for _ in range(5):
            detector.record_write("events", "EVENTS")

    # THEN a warning should be logged
    assert "Hot partition detected" in caplog.text
    assert 'table="events"' in caplog.text
    assert 'pk="EVENTS"' in caplog.text


def test_logs_warning_when_read_threshold_exceeded(caplog):
    """Logs warning when read threshold is exceeded."""
    # GIVEN a detector with low read threshold
    detector = HotPartitionDetector(
        writes_threshold=100,
        reads_threshold=5,
        window_seconds=60,
    )

    # WHEN we exceed the read threshold
    with caplog.at_level(logging.WARNING, logger="pydynox.diagnostics"):
        for _ in range(5):
            detector.record_read("config", "CONFIG")

    # THEN a warning should be logged
    assert "Hot partition detected" in caplog.text
    assert "reads" in caplog.text


def test_clear_resets_counts():
    """clear() resets all tracked counts."""
    # GIVEN a detector with recorded writes
    detector = HotPartitionDetector(
        writes_threshold=100,
        reads_threshold=300,
        window_seconds=60,
    )

    for _ in range(10):
        detector.record_write("users", "USER#1")

    assert detector.get_write_count("users", "USER#1") == 10

    # WHEN we clear
    detector.clear()

    # THEN counts should be reset
    assert detector.get_write_count("users", "USER#1") == 0


def test_client_accepts_diagnostics():
    """DynamoDBClient accepts diagnostics parameter."""
    # GIVEN a detector
    detector = HotPartitionDetector(
        writes_threshold=100,
        reads_threshold=300,
        window_seconds=60,
    )

    # WHEN we create a client with diagnostics
    with patch("pydynox.pydynox_core.DynamoDBClient"):
        client = DynamoDBClient(
            endpoint_url="http://localhost:4566",
            diagnostics=detector,
        )

    # THEN diagnostics should be set
    assert client.diagnostics is detector


def test_client_without_diagnostics():
    """DynamoDBClient works without diagnostics."""
    # WHEN we create a client without diagnostics
    with patch("pydynox.pydynox_core.DynamoDBClient"):
        client = DynamoDBClient(endpoint_url="http://localhost:4566")

    # THEN diagnostics should be None
    assert client.diagnostics is None


def test_table_override_writes_threshold():
    """set_table_thresholds overrides writes threshold for specific table."""
    # GIVEN a detector
    detector = HotPartitionDetector(
        writes_threshold=100,
        reads_threshold=300,
        window_seconds=60,
    )

    # WHEN we set higher threshold for a specific table
    detector.set_table_thresholds("events", writes_threshold=500)

    # THEN that table should use the override
    assert detector._get_writes_threshold("users") == 100
    assert detector._get_writes_threshold("events") == 500


def test_table_override_reads_threshold():
    """set_table_thresholds overrides reads threshold for specific table."""
    # GIVEN a detector
    detector = HotPartitionDetector(
        writes_threshold=100,
        reads_threshold=300,
        window_seconds=60,
    )

    # WHEN we set higher threshold for a specific table
    detector.set_table_thresholds("config_cache", reads_threshold=1000)

    # THEN that table should use the override
    assert detector._get_reads_threshold("users") == 300
    assert detector._get_reads_threshold("config_cache") == 1000


def test_table_override_both_thresholds():
    """set_table_thresholds can override both thresholds."""
    # GIVEN a detector
    detector = HotPartitionDetector(
        writes_threshold=100,
        reads_threshold=300,
        window_seconds=60,
    )

    # WHEN we override both thresholds
    detector.set_table_thresholds("events", writes_threshold=500, reads_threshold=1500)

    # THEN both should be overridden
    assert detector._get_writes_threshold("events") == 500
    assert detector._get_reads_threshold("events") == 1500


def test_table_override_partial():
    """set_table_thresholds with None keeps default."""
    # GIVEN a detector
    detector = HotPartitionDetector(
        writes_threshold=100,
        reads_threshold=300,
        window_seconds=60,
    )

    # WHEN we only override writes
    detector.set_table_thresholds("events", writes_threshold=500, reads_threshold=None)

    # THEN writes should be overridden, reads should use default
    assert detector._get_writes_threshold("events") == 500
    assert detector._get_reads_threshold("events") == 300


def test_clear_removes_table_overrides():
    """clear() also removes table overrides."""
    # GIVEN a detector with table override
    detector = HotPartitionDetector(
        writes_threshold=100,
        reads_threshold=300,
        window_seconds=60,
    )

    detector.set_table_thresholds("events", writes_threshold=500)
    assert detector._get_writes_threshold("events") == 500

    # WHEN we clear
    detector.clear()

    # THEN override should be removed
    assert detector._get_writes_threshold("events") == 100
