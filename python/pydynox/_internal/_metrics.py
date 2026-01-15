"""Internal metrics helpers."""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Any

from pydynox import pydynox_core

# Re-export OperationMetrics from Rust
OperationMetrics = pydynox_core.OperationMetrics


# Thread-local storage for KMS metrics during serialization
_kms_metrics_context = threading.local()


def _get_kms_metrics_accumulator() -> list[tuple[float, int]] | None:
    """Get the current KMS metrics accumulator, if any."""
    return getattr(_kms_metrics_context, "accumulator", None)


def _start_kms_metrics_collection() -> None:
    """Start collecting KMS metrics for the current operation."""
    _kms_metrics_context.accumulator = []


def _stop_kms_metrics_collection() -> tuple[float, int]:
    """Stop collecting and return total (duration_ms, calls)."""
    accumulator = getattr(_kms_metrics_context, "accumulator", None)
    _kms_metrics_context.accumulator = None

    if not accumulator:
        return 0.0, 0

    total_duration = sum(d for d, _ in accumulator)
    total_calls = sum(c for _, c in accumulator)
    return total_duration, total_calls


def _record_kms_metrics(duration_ms: float, calls: int = 1) -> None:
    """Record KMS metrics if collection is active."""
    accumulator = getattr(_kms_metrics_context, "accumulator", None)
    if accumulator is not None:
        accumulator.append((duration_ms, calls))


class ListWithMetrics(list[dict[str, Any]]):
    """A list subclass that carries operation metrics and pagination token.

    Used for PartiQL results where we return a list of items with metrics.
    """

    def __init__(
        self,
        items: list[dict[str, Any]],
        metrics: OperationMetrics,
        next_token: str | None = None,
    ) -> None:
        super().__init__(items)
        self.metrics = metrics
        self.next_token = next_token


@dataclass
class ModelMetrics:
    """Aggregated metrics for a Model class.

    Tracks total RCU/WCU consumed, operation counts, and KMS metrics.
    """

    total_rcu: float = 0.0
    total_wcu: float = 0.0
    total_duration_ms: float = 0.0
    operation_count: int = 0
    get_count: int = 0
    put_count: int = 0
    delete_count: int = 0
    update_count: int = 0
    query_count: int = 0
    scan_count: int = 0
    # KMS metrics
    kms_duration_ms: float = 0.0
    kms_calls: int = 0

    def add(self, metrics: OperationMetrics, operation: str) -> None:
        """Add metrics from an operation.

        Args:
            metrics: The OperationMetrics from the operation.
            operation: The operation type (get, put, delete, update, query, scan).
        """
        if metrics.consumed_rcu is not None:
            self.total_rcu += metrics.consumed_rcu
        if metrics.consumed_wcu is not None:
            self.total_wcu += metrics.consumed_wcu
        self.total_duration_ms += metrics.duration_ms
        self.operation_count += 1

        if operation == "get":
            self.get_count += 1
        elif operation == "put":
            self.put_count += 1
        elif operation == "delete":
            self.delete_count += 1
        elif operation == "update":
            self.update_count += 1
        elif operation == "query":
            self.query_count += 1
        elif operation == "scan":
            self.scan_count += 1

    def add_kms(self, duration_ms: float, calls: int = 1) -> None:
        """Add KMS metrics.

        Args:
            duration_ms: Time spent on KMS call.
            calls: Number of KMS API calls (default 1).
        """
        self.kms_duration_ms += duration_ms
        self.kms_calls += calls

    def reset(self) -> None:
        """Reset all metrics to zero."""
        self.total_rcu = 0.0
        self.total_wcu = 0.0
        self.total_duration_ms = 0.0
        self.operation_count = 0
        self.get_count = 0
        self.put_count = 0
        self.delete_count = 0
        self.update_count = 0
        self.query_count = 0
        self.scan_count = 0
        self.kms_duration_ms = 0.0
        self.kms_calls = 0


@dataclass
class MetricsStorage:
    """Storage for last and total metrics per Model class.

    Each Model class gets its own MetricsStorage instance.
    """

    last: OperationMetrics | None = None
    total: ModelMetrics = field(default_factory=ModelMetrics)

    def record(self, metrics: OperationMetrics, operation: str) -> None:
        """Record metrics from an operation.

        Args:
            metrics: The OperationMetrics from the operation.
            operation: The operation type.
        """
        self.last = metrics
        self.total.add(metrics, operation)

    def reset(self) -> None:
        """Reset all metrics."""
        self.last = None
        self.total.reset()
