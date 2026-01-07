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
    detector = HotPartitionDetector(
        writes_threshold=100,
        reads_threshold=300,
        window_seconds=30,
    )

    assert detector.writes_threshold == 100
    assert detector.reads_threshold == 300
    assert detector.window_seconds == 30


def test_record_write_tracks_count():
    """record_write tracks write count per partition."""
    detector = HotPartitionDetector(
        writes_threshold=100,
        reads_threshold=300,
        window_seconds=60,
    )

    for _ in range(5):
        detector.record_write("users", "USER#1")

    assert detector.get_write_count("users", "USER#1") == 5
    assert detector.get_write_count("users", "USER#2") == 0


def test_record_read_tracks_count():
    """record_read tracks read count per partition."""
    detector = HotPartitionDetector(
        writes_threshold=100,
        reads_threshold=300,
        window_seconds=60,
    )

    for _ in range(10):
        detector.record_read("orders", "ORDER#1")

    assert detector.get_read_count("orders", "ORDER#1") == 10


def test_separate_tables_tracked_separately():
    """Different tables are tracked separately."""
    detector = HotPartitionDetector(
        writes_threshold=100,
        reads_threshold=300,
        window_seconds=60,
    )

    for _ in range(3):
        detector.record_write("users", "PK#1")
        detector.record_write("orders", "PK#1")

    assert detector.get_write_count("users", "PK#1") == 3
    assert detector.get_write_count("orders", "PK#1") == 3


def test_logs_warning_when_threshold_exceeded(caplog):
    """Logs warning when write threshold is exceeded."""
    detector = HotPartitionDetector(
        writes_threshold=5,
        reads_threshold=10,
        window_seconds=60,
    )

    with caplog.at_level(logging.WARNING, logger="pydynox.diagnostics"):
        for _ in range(5):
            detector.record_write("events", "EVENTS")

    assert "Hot partition detected" in caplog.text
    assert 'table="events"' in caplog.text
    assert 'pk="EVENTS"' in caplog.text


def test_logs_warning_when_read_threshold_exceeded(caplog):
    """Logs warning when read threshold is exceeded."""
    detector = HotPartitionDetector(
        writes_threshold=100,
        reads_threshold=5,
        window_seconds=60,
    )

    with caplog.at_level(logging.WARNING, logger="pydynox.diagnostics"):
        for _ in range(5):
            detector.record_read("config", "CONFIG")

    assert "Hot partition detected" in caplog.text
    assert "reads" in caplog.text


def test_clear_resets_counts():
    """clear() resets all tracked counts."""
    detector = HotPartitionDetector(
        writes_threshold=100,
        reads_threshold=300,
        window_seconds=60,
    )

    for _ in range(10):
        detector.record_write("users", "USER#1")

    assert detector.get_write_count("users", "USER#1") == 10

    detector.clear()

    assert detector.get_write_count("users", "USER#1") == 0


def test_client_accepts_diagnostics():
    """DynamoDBClient accepts diagnostics parameter."""
    detector = HotPartitionDetector(
        writes_threshold=100,
        reads_threshold=300,
        window_seconds=60,
    )

    with patch("pydynox.pydynox_core.DynamoDBClient"):
        client = DynamoDBClient(
            endpoint_url="http://localhost:4566",
            diagnostics=detector,
        )

    assert client.diagnostics is detector


def test_client_without_diagnostics():
    """DynamoDBClient works without diagnostics."""
    with patch("pydynox.pydynox_core.DynamoDBClient"):
        client = DynamoDBClient(endpoint_url="http://localhost:4566")

    assert client.diagnostics is None


def test_table_override_writes_threshold():
    """set_table_thresholds overrides writes threshold for specific table."""
    detector = HotPartitionDetector(
        writes_threshold=100,
        reads_threshold=300,
        window_seconds=60,
    )

    # Set higher threshold for high-traffic table
    detector.set_table_thresholds("events", writes_threshold=500)

    assert detector._get_writes_threshold("users") == 100
    assert detector._get_writes_threshold("events") == 500


def test_table_override_reads_threshold():
    """set_table_thresholds overrides reads threshold for specific table."""
    detector = HotPartitionDetector(
        writes_threshold=100,
        reads_threshold=300,
        window_seconds=60,
    )

    # Set higher threshold for cache table
    detector.set_table_thresholds("config_cache", reads_threshold=1000)

    assert detector._get_reads_threshold("users") == 300
    assert detector._get_reads_threshold("config_cache") == 1000


def test_table_override_both_thresholds():
    """set_table_thresholds can override both thresholds."""
    detector = HotPartitionDetector(
        writes_threshold=100,
        reads_threshold=300,
        window_seconds=60,
    )

    detector.set_table_thresholds("events", writes_threshold=500, reads_threshold=1500)

    assert detector._get_writes_threshold("events") == 500
    assert detector._get_reads_threshold("events") == 1500


def test_table_override_partial():
    """set_table_thresholds with None keeps default."""
    detector = HotPartitionDetector(
        writes_threshold=100,
        reads_threshold=300,
        window_seconds=60,
    )

    # Only override writes, keep default reads
    detector.set_table_thresholds("events", writes_threshold=500, reads_threshold=None)

    assert detector._get_writes_threshold("events") == 500
    assert detector._get_reads_threshold("events") == 300


def test_clear_removes_table_overrides():
    """clear() also removes table overrides."""
    detector = HotPartitionDetector(
        writes_threshold=100,
        reads_threshold=300,
        window_seconds=60,
    )

    detector.set_table_thresholds("events", writes_threshold=500)
    assert detector._get_writes_threshold("events") == 500

    detector.clear()

    assert detector._get_writes_threshold("events") == 100
