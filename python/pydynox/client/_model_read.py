"""Client views used only by model reads."""

from __future__ import annotations

from functools import partial
from typing import Any

from pydynox._internal._decimal import NumberSchema
from pydynox._internal._metrics import OperationMetrics
from pydynox.client._client import DynamoDBClient

_READ_METHODS = frozenset(
    f"{prefix}{method}"
    for prefix in ("", "sync_")
    for method in (
        "get_item",
        "query_page",
        "scan_page",
        "parallel_scan",
        "batch_get",
        "execute_statement",
        "search_vectors",
    )
)


class _NativeModelClient:
    def __init__(self, client: Any, schema: NumberSchema):
        self._source = client
        self._schema = schema

    def __getattr__(self, name: str) -> Any:
        method = getattr(self._source, name)
        if name in _READ_METHODS:
            return partial(method, _number_schema=self._schema)
        return method


class _ModelReadClient(DynamoDBClient):
    """Reuse normal operations, tracing, and rate limits with a private decoder."""

    _client: Any

    def __init__(self, client: DynamoDBClient, schema: NumberSchema):
        self._source = client
        self._client = _NativeModelClient(client._client, schema)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._source, name)

    def _record_metrics(self, metrics: OperationMetrics, operation: str) -> None:
        self._source._record_metrics(metrics, operation)
