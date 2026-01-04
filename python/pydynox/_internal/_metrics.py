"""Internal metrics helpers."""

from __future__ import annotations

from typing import Any

from pydynox import pydynox_core

# Re-export OperationMetrics from Rust
OperationMetrics = pydynox_core.OperationMetrics


class DictWithMetrics(dict[str, Any]):
    """A dict subclass that carries operation metrics.

    Internal class - users just see a dict with .metrics attribute.
    """

    metrics: OperationMetrics

    def __init__(self, data: dict[str, Any], metrics: OperationMetrics):
        super().__init__(data)
        self.metrics = metrics


class ListWithMetrics(list[dict[str, Any]]):
    """A list subclass that carries operation metrics and pagination token.

    Used for PartiQL results - users iterate over items and access .metrics/.next_token.
    """

    metrics: OperationMetrics
    next_token: str | None

    def __init__(
        self,
        items: list[dict[str, Any]],
        metrics: OperationMetrics,
        next_token: str | None = None,
    ):
        super().__init__(items)
        self.metrics = metrics
        self.next_token = next_token
