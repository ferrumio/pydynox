"""Type stubs for mixin classes.

At runtime this module exports `_MixinBase = object` so it has zero cost.
Under TYPE_CHECKING, _MixinBase declares the interface that BaseClient provides,
allowing type checkers to resolve attributes used by mixin classes.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pydynox._internal._metrics import ModelMetrics, OperationMetrics

    class _MixinBase:
        _client: Any  # pydynox_core.DynamoDBClient (Rust extension)
        _last_metrics: OperationMetrics | None
        _total_metrics: ModelMetrics

        def _acquire_rcu(self, rcu: float = 1.0) -> None: ...
        def _acquire_wcu(self, wcu: float = 1.0) -> None: ...
        def _on_throttle(self) -> None: ...
        def _record_write(self, table: str, pk: str) -> None: ...
        def _record_read(self, table: str, pk: str) -> None: ...
        def _record_metrics(self, metrics: OperationMetrics, operation: str) -> None: ...
        def get_region(self) -> str: ...

else:
    _MixinBase = object
