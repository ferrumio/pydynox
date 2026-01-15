"""Tests for KMS metrics collection."""

from pydynox._internal._metrics import (
    ModelMetrics,
    _record_kms_metrics,
    _start_kms_metrics_collection,
    _stop_kms_metrics_collection,
)


def test_kms_metrics_collection_basic():
    """KMS metrics are collected during active collection."""
    # GIVEN an active metrics collection
    _start_kms_metrics_collection()

    # WHEN we record metrics
    _record_kms_metrics(10.0, 1)
    _record_kms_metrics(20.0, 1)

    # THEN stop should return accumulated values
    duration, calls = _stop_kms_metrics_collection()

    assert duration == 30.0
    assert calls == 2


def test_kms_metrics_collection_not_active():
    """Recording without active collection does nothing."""
    # GIVEN no active collection (no start)

    # WHEN we record metrics
    _record_kms_metrics(10.0, 1)

    # THEN stop should return zeros
    duration, calls = _stop_kms_metrics_collection()

    assert duration == 0.0
    assert calls == 0


def test_kms_metrics_collection_stop_clears():
    """Stop clears the accumulator."""
    # GIVEN an active collection with recorded metrics
    _start_kms_metrics_collection()
    _record_kms_metrics(10.0, 1)
    _stop_kms_metrics_collection()

    # WHEN we stop again
    duration, calls = _stop_kms_metrics_collection()

    # THEN it should return zeros
    assert duration == 0.0
    assert calls == 0


def test_model_metrics_add_kms():
    """ModelMetrics.add_kms adds KMS metrics."""
    # GIVEN a ModelMetrics instance
    metrics = ModelMetrics()

    # WHEN we add KMS metrics
    metrics.add_kms(10.0, 1)
    metrics.add_kms(20.0, 2)

    # THEN metrics should be accumulated
    assert metrics.kms_duration_ms == 30.0
    assert metrics.kms_calls == 3


def test_model_metrics_reset_clears_kms():
    """ModelMetrics.reset clears KMS metrics."""
    # GIVEN a ModelMetrics instance with KMS metrics
    metrics = ModelMetrics()
    metrics.add_kms(10.0, 1)

    # WHEN we reset
    metrics.reset()

    # THEN KMS metrics should be cleared
    assert metrics.kms_duration_ms == 0.0
    assert metrics.kms_calls == 0


def test_model_metrics_default_kms_values():
    """ModelMetrics has zero KMS values by default."""
    # WHEN we create a new ModelMetrics
    metrics = ModelMetrics()

    # THEN KMS values should be zero
    assert metrics.kms_duration_ms == 0.0
    assert metrics.kms_calls == 0
