"""Tests for KMS metrics collection."""

from pydynox._internal._metrics import (
    ModelMetrics,
    _record_kms_metrics,
    _start_kms_metrics_collection,
    _stop_kms_metrics_collection,
)


def test_kms_metrics_collection_basic():
    """KMS metrics are collected during active collection."""
    _start_kms_metrics_collection()
    _record_kms_metrics(10.0, 1)
    _record_kms_metrics(20.0, 1)
    duration, calls = _stop_kms_metrics_collection()

    assert duration == 30.0
    assert calls == 2


def test_kms_metrics_collection_not_active():
    """Recording without active collection does nothing."""
    # No start, so recording should be ignored
    _record_kms_metrics(10.0, 1)
    duration, calls = _stop_kms_metrics_collection()

    assert duration == 0.0
    assert calls == 0


def test_kms_metrics_collection_stop_clears():
    """Stop clears the accumulator."""
    _start_kms_metrics_collection()
    _record_kms_metrics(10.0, 1)
    _stop_kms_metrics_collection()

    # Second stop should return zeros
    duration, calls = _stop_kms_metrics_collection()
    assert duration == 0.0
    assert calls == 0


def test_model_metrics_add_kms():
    """ModelMetrics.add_kms adds KMS metrics."""
    metrics = ModelMetrics()
    metrics.add_kms(10.0, 1)
    metrics.add_kms(20.0, 2)

    assert metrics.kms_duration_ms == 30.0
    assert metrics.kms_calls == 3


def test_model_metrics_reset_clears_kms():
    """ModelMetrics.reset clears KMS metrics."""
    metrics = ModelMetrics()
    metrics.add_kms(10.0, 1)
    metrics.reset()

    assert metrics.kms_duration_ms == 0.0
    assert metrics.kms_calls == 0


def test_model_metrics_default_kms_values():
    """ModelMetrics has zero KMS values by default."""
    metrics = ModelMetrics()

    assert metrics.kms_duration_ms == 0.0
    assert metrics.kms_calls == 0
