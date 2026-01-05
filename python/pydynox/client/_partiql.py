"""PartiQL operations (sync + async)."""

from __future__ import annotations

from typing import Any

from pydynox._internal._logging import _log_operation, _log_warning
from pydynox._internal._metrics import ListWithMetrics

_SLOW_QUERY_THRESHOLD_MS = 100.0


class PartiqlOperations:
    """PartiQL statement execution."""

    def execute_statement(
        self,
        statement: str,
        parameters: list[Any] | None = None,
        consistent_read: bool = False,
        next_token: str | None = None,
    ) -> ListWithMetrics:
        """Execute a PartiQL statement."""
        self._acquire_rcu(1.0)  # type: ignore[attr-defined]
        items, next_token_out, metrics = self._client.execute_statement(  # type: ignore[attr-defined]
            statement,
            parameters=parameters,
            consistent_read=consistent_read,
            next_token=next_token,
        )
        _log_operation(
            "execute_statement",
            statement[:50],
            metrics.duration_ms,
            consumed_rcu=metrics.consumed_rcu,
        )
        if metrics.duration_ms > _SLOW_QUERY_THRESHOLD_MS:
            _log_warning("execute_statement", f"slow operation ({metrics.duration_ms:.1f}ms)")
        return ListWithMetrics(items, metrics, next_token_out)

    async def async_execute_statement(
        self,
        statement: str,
        parameters: list[Any] | None = None,
        consistent_read: bool = False,
        next_token: str | None = None,
    ) -> ListWithMetrics:
        """Async version of execute_statement."""
        self._acquire_rcu(1.0)  # type: ignore[attr-defined]
        result = await self._client.async_execute_statement(  # type: ignore[attr-defined]
            statement,
            parameters=parameters,
            consistent_read=consistent_read,
            next_token=next_token,
        )
        metrics = result["metrics"]
        _log_operation(
            "execute_statement",
            statement[:50],
            metrics.duration_ms,
            consumed_rcu=metrics.consumed_rcu,
        )
        if metrics.duration_ms > _SLOW_QUERY_THRESHOLD_MS:
            _log_warning("execute_statement", f"slow operation ({metrics.duration_ms:.1f}ms)")
        return ListWithMetrics(result["items"], metrics, result["next_token"])
