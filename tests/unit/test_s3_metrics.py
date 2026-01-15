"""Unit tests for S3 metrics."""

from pydynox._internal._metrics import ModelMetrics
from pydynox._internal._operations_metrics import (
    _record_s3_metrics,
    _start_s3_metrics_collection,
    _stop_s3_metrics_collection,
)


def test_s3_metrics_collection_basic():
    """S3 metrics collection records duration, calls, and bytes."""
    # GIVEN we start S3 metrics collection
    _start_s3_metrics_collection()

    # WHEN we record metrics
    _record_s3_metrics(100.0, 1, 1024, 0)

    # THEN stop should return the totals
    duration, calls, uploaded, downloaded = _stop_s3_metrics_collection()
    assert duration == 100.0
    assert calls == 1
    assert uploaded == 1024
    assert downloaded == 0


def test_s3_metrics_collection_multiple_records():
    """S3 metrics collection accumulates multiple records."""
    # GIVEN we start S3 metrics collection
    _start_s3_metrics_collection()

    # WHEN we record multiple metrics
    _record_s3_metrics(50.0, 1, 512, 0)  # Upload
    _record_s3_metrics(30.0, 1, 0, 256)  # Download
    _record_s3_metrics(20.0, 1, 128, 0)  # Another upload

    # THEN stop should return accumulated totals
    duration, calls, uploaded, downloaded = _stop_s3_metrics_collection()
    assert duration == 100.0
    assert calls == 3
    assert uploaded == 640
    assert downloaded == 256


def test_s3_metrics_collection_no_records():
    """S3 metrics collection returns zeros when no records."""
    # GIVEN we start S3 metrics collection
    _start_s3_metrics_collection()

    # WHEN we don't record anything
    # THEN stop should return zeros
    duration, calls, uploaded, downloaded = _stop_s3_metrics_collection()
    assert duration == 0.0
    assert calls == 0
    assert uploaded == 0
    assert downloaded == 0


def test_s3_metrics_not_recorded_without_collection():
    """S3 metrics are not recorded when collection is not active."""
    # GIVEN collection is not started
    # WHEN we try to record metrics
    _record_s3_metrics(100.0, 1, 1024, 0)

    # THEN stop should return zeros (nothing was collected)
    duration, calls, uploaded, downloaded = _stop_s3_metrics_collection()
    assert duration == 0.0
    assert calls == 0
    assert uploaded == 0
    assert downloaded == 0


def test_model_metrics_add_s3():
    """ModelMetrics.add_s3() accumulates S3 metrics."""
    # GIVEN a ModelMetrics instance
    metrics = ModelMetrics()

    # WHEN we add S3 metrics
    metrics.add_s3(100.0, 2, 1024, 512)

    # THEN S3 metrics should be set
    assert metrics.s3_duration_ms == 100.0
    assert metrics.s3_calls == 2
    assert metrics.s3_bytes_uploaded == 1024
    assert metrics.s3_bytes_downloaded == 512


def test_model_metrics_add_s3_accumulates():
    """ModelMetrics.add_s3() accumulates multiple calls."""
    # GIVEN a ModelMetrics instance
    metrics = ModelMetrics()

    # WHEN we add S3 metrics multiple times
    metrics.add_s3(50.0, 1, 512, 0)
    metrics.add_s3(30.0, 1, 0, 256)
    metrics.add_s3(20.0, 2, 128, 128)

    # THEN S3 metrics should be accumulated
    assert metrics.s3_duration_ms == 100.0
    assert metrics.s3_calls == 4
    assert metrics.s3_bytes_uploaded == 640
    assert metrics.s3_bytes_downloaded == 384


def test_model_metrics_reset_clears_s3():
    """ModelMetrics.reset() clears S3 metrics."""
    # GIVEN a ModelMetrics instance with S3 metrics
    metrics = ModelMetrics()
    metrics.add_s3(100.0, 2, 1024, 512)

    # WHEN we reset
    metrics.reset()

    # THEN S3 metrics should be zero
    assert metrics.s3_duration_ms == 0.0
    assert metrics.s3_calls == 0
    assert metrics.s3_bytes_uploaded == 0
    assert metrics.s3_bytes_downloaded == 0


def test_model_metrics_s3_defaults():
    """ModelMetrics has S3 fields with zero defaults."""
    # WHEN we create a new ModelMetrics
    metrics = ModelMetrics()

    # THEN S3 fields should be zero
    assert metrics.s3_duration_ms == 0.0
    assert metrics.s3_calls == 0
    assert metrics.s3_bytes_uploaded == 0
    assert metrics.s3_bytes_downloaded == 0
