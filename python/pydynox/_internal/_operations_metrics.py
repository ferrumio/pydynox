"""Thread-local metrics collection for KMS and S3 operations.

This module handles accumulating metrics during Model operations.
KMS metrics are collected during serialization/deserialization.
S3 metrics are collected during file uploads/downloads.
"""

from __future__ import annotations

import threading

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


# Thread-local storage for S3 metrics during operations
_s3_metrics_context = threading.local()


def _start_s3_metrics_collection() -> None:
    """Start collecting S3 metrics for the current operation."""
    _s3_metrics_context.accumulator = []


def _stop_s3_metrics_collection() -> tuple[float, int, int, int]:
    """Stop collecting and return total (duration_ms, calls, bytes_uploaded, bytes_downloaded)."""
    accumulator = getattr(_s3_metrics_context, "accumulator", None)
    _s3_metrics_context.accumulator = None

    if not accumulator:
        return 0.0, 0, 0, 0

    total_duration = sum(d for d, _, _, _ in accumulator)
    total_calls = sum(c for _, c, _, _ in accumulator)
    total_uploaded = sum(u for _, _, u, _ in accumulator)
    total_downloaded = sum(d for _, _, _, d in accumulator)
    return total_duration, total_calls, total_uploaded, total_downloaded


def _record_s3_metrics(
    duration_ms: float, calls: int, bytes_uploaded: int, bytes_downloaded: int
) -> None:
    """Record S3 metrics if collection is active."""
    accumulator = getattr(_s3_metrics_context, "accumulator", None)
    if accumulator is not None:
        accumulator.append((duration_ms, calls, bytes_uploaded, bytes_downloaded))
