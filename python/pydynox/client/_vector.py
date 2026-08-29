"""Vector search and vector index operations."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pydynox._internal._logging import _log_debug
from pydynox._internal._tracing import add_response_attributes, trace_operation
from pydynox._internal._vector import VectorMatch, VectorSearchResult
from pydynox.client._typing import _MixinBase

if TYPE_CHECKING:  # pragma: no cover
    from collections.abc import Coroutine


def _convert_search_result(value: dict[str, Any]) -> VectorSearchResult[dict[str, Any]]:
    matches = [VectorMatch(item=match["item"], score=match["score"]) for match in value["matches"]]
    return VectorSearchResult(matches, value["metrics"])


class VectorOperations(_MixinBase):  # pragma: no cover
    """DynamoDB vector operations."""

    async def search_vectors(
        self,
        table: str,
        index_name: str,
        vector: list[float],
        *,
        top_k: int = 10,
        search_condition_expression: str | None = None,
        expression_attribute_names: dict[str, str] | None = None,
        expression_attribute_values: dict[str, Any] | None = None,
        projection_expression: str | None = None,
    ) -> VectorSearchResult[dict[str, Any]]:
        _log_debug("search_vectors", f'Searching vector index "{index_name}"')
        with trace_operation("search_vectors", table, self.get_region()) as span:
            value = await self._client.search_vectors(  # type: ignore[attr-defined]
                table,
                index_name,
                vector,
                top_k=top_k,
                search_condition_expression=search_condition_expression,
                expression_attribute_names=expression_attribute_names,
                expression_attribute_values=expression_attribute_values,
                projection_expression=projection_expression,
            )
            result = _convert_search_result(value)
            if span is not None:
                span.set_attribute("aws.dynamodb.vector_index", index_name)
            add_response_attributes(
                span,
                request_id=result.metrics.request_id,
                vector_search_bytes=result.metrics.vector_search_bytes,
                returned_rows=len(result),
            )
        self._record_metrics(result.metrics, "vector_search")
        return result

    def sync_search_vectors(
        self,
        table: str,
        index_name: str,
        vector: list[float],
        *,
        top_k: int = 10,
        search_condition_expression: str | None = None,
        expression_attribute_names: dict[str, str] | None = None,
        expression_attribute_values: dict[str, Any] | None = None,
        projection_expression: str | None = None,
    ) -> VectorSearchResult[dict[str, Any]]:
        _log_debug("sync_search_vectors", f'Searching vector index "{index_name}"')
        with trace_operation("search_vectors", table, self.get_region()) as span:
            value = self._client.sync_search_vectors(  # type: ignore[attr-defined]
                table,
                index_name,
                vector,
                top_k=top_k,
                search_condition_expression=search_condition_expression,
                expression_attribute_names=expression_attribute_names,
                expression_attribute_values=expression_attribute_values,
                projection_expression=projection_expression,
            )
            result = _convert_search_result(value)
            if span is not None:
                span.set_attribute("aws.dynamodb.vector_index", index_name)
            add_response_attributes(
                span,
                request_id=result.metrics.request_id,
                vector_search_bytes=result.metrics.vector_search_bytes,
                returned_rows=len(result),
            )
        self._record_metrics(result.metrics, "vector_search")
        return result

    def create_vector_index(
        self,
        table: str,
        definition: dict[str, Any],
        *,
        wait: bool = False,
    ) -> Coroutine[Any, Any, None]:
        _log_debug("create_vector_index", f'Creating vector index on "{table}"')
        return self._client.create_vector_index(  # type: ignore[attr-defined, no-any-return]
            table, definition, wait=wait
        )

    def sync_create_vector_index(
        self,
        table: str,
        definition: dict[str, Any],
        *,
        wait: bool = False,
    ) -> None:
        _log_debug("sync_create_vector_index", f'Creating vector index on "{table}"')
        self._client.sync_create_vector_index(  # type: ignore[attr-defined]
            table, definition, wait=wait
        )

    def delete_vector_index(
        self,
        table: str,
        index_name: str,
        *,
        wait: bool = False,
    ) -> Coroutine[Any, Any, None]:
        _log_debug("delete_vector_index", f'Deleting vector index "{index_name}"')
        return self._client.delete_vector_index(  # type: ignore[attr-defined, no-any-return]
            table, index_name, wait=wait
        )

    def sync_delete_vector_index(
        self,
        table: str,
        index_name: str,
        *,
        wait: bool = False,
    ) -> None:
        _log_debug("sync_delete_vector_index", f'Deleting vector index "{index_name}"')
        self._client.sync_delete_vector_index(  # type: ignore[attr-defined]
            table, index_name, wait=wait
        )

    def describe_vector_index(
        self,
        table: str,
        index_name: str,
    ) -> Coroutine[Any, Any, dict[str, Any]]:
        return self._client.describe_vector_index(  # type: ignore[attr-defined, no-any-return]
            table, index_name
        )

    def sync_describe_vector_index(
        self,
        table: str,
        index_name: str,
    ) -> dict[str, Any]:
        return self._client.sync_describe_vector_index(  # type: ignore[attr-defined, no-any-return]
            table, index_name
        )
