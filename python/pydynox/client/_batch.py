"""Batch and transaction operations."""

from __future__ import annotations

from typing import Any


class BatchOperations:
    """Batch and transaction operations."""

    # ========== BATCH WRITE ==========

    def batch_write(
        self,
        table: str,
        put_items: list[dict[str, Any]] | None = None,
        delete_keys: list[dict[str, Any]] | None = None,
    ) -> None:
        """Batch write items to a DynamoDB table.

        Writes multiple items in a single request. Handles:
        - Splitting requests to respect the 25-item limit per batch
        - Retrying unprocessed items with exponential backoff
        """
        put_count = len(put_items) if put_items else 0
        delete_count = len(delete_keys) if delete_keys else 0
        self._acquire_wcu(float(put_count + delete_count))  # type: ignore[attr-defined]
        self._client.batch_write(  # type: ignore[attr-defined]
            table,
            put_items or [],
            delete_keys or [],
        )

    # ========== BATCH GET ==========

    def batch_get(
        self,
        table: str,
        keys: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Batch get items from a DynamoDB table.

        Gets multiple items in a single request. Handles:
        - Splitting requests to respect the 100-item limit per batch
        - Retrying unprocessed keys with exponential backoff
        - Combining results from multiple requests
        """
        self._acquire_rcu(float(len(keys)))  # type: ignore[attr-defined]
        return self._client.batch_get(table, keys)  # type: ignore[attr-defined, no-any-return]

    # ========== TRANSACT WRITE ==========

    def transact_write(self, operations: list[dict[str, Any]]) -> None:
        """Execute a transactional write operation.

        All operations run atomically. Either all succeed or all fail.
        """
        self._client.transact_write(operations)  # type: ignore[attr-defined]
