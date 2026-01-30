"""Table management operations.

Async-first API:
- create_table(), delete_table(), table_exists() - async (default)
- sync_create_table(), sync_delete_table(), sync_table_exists() - sync

Coverage note: This module is a thin wrapper around Rust client methods.
Lines are covered by integration tests, not unit tests. The TYPE_CHECKING
block and method bodies show as uncovered in unit test coverage because
they delegate directly to self._client (Rust).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:  # pragma: no cover
    from collections.abc import Coroutine


class TableOperations:  # pragma: no cover
    """Table management operations: create, delete, exists, wait.

    Async-first API:
    - Async methods (no prefix): create_table(), delete_table(), table_exists()
    - Sync methods (sync_ prefix): sync_create_table(), sync_delete_table(), sync_table_exists()

    Note: This class is excluded from unit test coverage because all methods
    are thin wrappers that delegate to self._client (Rust). Coverage is
    provided by integration tests.
    """

    # ========== ASYNC METHODS (default, no prefix) ==========

    def create_table(
        self,
        table_name: str,
        partition_key: tuple[str, str],
        sort_key: tuple[str, str] | None = None,
        billing_mode: str = "PAY_PER_REQUEST",
        read_capacity: int | None = None,
        write_capacity: int | None = None,
        table_class: str | None = None,
        encryption: str | None = None,
        kms_key_id: str | None = None,
        global_secondary_indexes: list[dict[str, Any]] | None = None,
        local_secondary_indexes: list[dict[str, Any]] | None = None,
        wait: bool = False,
    ) -> Coroutine[Any, Any, None]:
        """Create a new DynamoDB table. Returns an awaitable.

        Args:
            table_name: Name of the table to create.
            partition_key: Tuple of (attribute_name, attribute_type). Type is "S", "N", or "B".
            sort_key: Optional tuple of (attribute_name, attribute_type).
            billing_mode: "PAY_PER_REQUEST" (default) or "PROVISIONED".
            read_capacity: Read capacity units (only for PROVISIONED).
            write_capacity: Write capacity units (only for PROVISIONED).
            table_class: "STANDARD" (default) or "STANDARD_INFREQUENT_ACCESS".
            encryption: "AWS_OWNED", "AWS_MANAGED", or "CUSTOMER_MANAGED".
            kms_key_id: KMS key ARN (required for CUSTOMER_MANAGED).
            global_secondary_indexes: List of GSI definitions.
            local_secondary_indexes: List of LSI definitions.
            wait: If True, wait for table to become active.

        Returns:
            Awaitable that completes when table is created.

        Example:
            await client.create_table("users", partition_key=("pk", "S"))
        """
        return self._client.create_table(  # type: ignore[attr-defined, no-any-return]
            table_name,
            partition_key,
            range_key=sort_key,  # Rust uses range_key
            billing_mode=billing_mode,
            read_capacity=read_capacity,
            write_capacity=write_capacity,
            table_class=table_class,
            encryption=encryption,
            kms_key_id=kms_key_id,
            global_secondary_indexes=global_secondary_indexes,
            local_secondary_indexes=local_secondary_indexes,
            wait=wait,
        )

    def table_exists(self, table_name: str) -> Coroutine[Any, Any, bool]:
        """Check if a table exists. Returns an awaitable.

        Args:
            table_name: Name of the table to check.

        Returns:
            Awaitable that resolves to True if table exists, False otherwise.

        Example:
            exists = await client.table_exists("users")
        """
        return self._client.table_exists(table_name)  # type: ignore[attr-defined, no-any-return]

    def delete_table(self, table_name: str) -> Coroutine[Any, Any, None]:
        """Delete a table. Returns an awaitable.

        Args:
            table_name: Name of the table to delete.

        Returns:
            Awaitable that completes when table is deleted.

        Example:
            await client.delete_table("users")
        """
        return self._client.delete_table(table_name)  # type: ignore[attr-defined, no-any-return]

    def wait_for_table_active(
        self,
        table_name: str,
        timeout_seconds: int | None = None,
    ) -> Coroutine[Any, Any, None]:
        """Wait for a table to become active. Returns an awaitable.

        Args:
            table_name: Name of the table to wait for.
            timeout_seconds: Maximum time to wait (default: 60).

        Returns:
            Awaitable that completes when table is active.

        Example:
            await client.wait_for_table_active("users")
        """
        return self._client.wait_for_table_active(  # type: ignore[attr-defined, no-any-return]
            table_name, timeout_seconds=timeout_seconds
        )

    # ========== SYNC METHODS (sync_ prefix) ==========

    def sync_create_table(
        self,
        table_name: str,
        partition_key: tuple[str, str],
        sort_key: tuple[str, str] | None = None,
        billing_mode: str = "PAY_PER_REQUEST",
        read_capacity: int | None = None,
        write_capacity: int | None = None,
        table_class: str | None = None,
        encryption: str | None = None,
        kms_key_id: str | None = None,
        global_secondary_indexes: list[dict[str, Any]] | None = None,
        local_secondary_indexes: list[dict[str, Any]] | None = None,
        wait: bool = False,
    ) -> None:
        """Create a new DynamoDB table. Blocks until complete.

        Args:
            table_name: Name of the table to create.
            partition_key: Tuple of (attribute_name, attribute_type). Type is "S", "N", or "B".
            sort_key: Optional tuple of (attribute_name, attribute_type).
            billing_mode: "PAY_PER_REQUEST" (default) or "PROVISIONED".
            read_capacity: Read capacity units (only for PROVISIONED).
            write_capacity: Write capacity units (only for PROVISIONED).
            table_class: "STANDARD" (default) or "STANDARD_INFREQUENT_ACCESS".
            encryption: "AWS_OWNED", "AWS_MANAGED", or "CUSTOMER_MANAGED".
            kms_key_id: KMS key ARN (required for CUSTOMER_MANAGED).
            global_secondary_indexes: List of GSI definitions.
            local_secondary_indexes: List of LSI definitions.
            wait: If True, wait for table to become active.

        Example:
            client.sync_create_table("users", partition_key=("pk", "S"))
        """
        self._client.sync_create_table(  # type: ignore[attr-defined]
            table_name,
            partition_key,
            range_key=sort_key,  # Rust uses range_key
            billing_mode=billing_mode,
            read_capacity=read_capacity,
            write_capacity=write_capacity,
            table_class=table_class,
            encryption=encryption,
            kms_key_id=kms_key_id,
            global_secondary_indexes=global_secondary_indexes,
            local_secondary_indexes=local_secondary_indexes,
            wait=wait,
        )

    def sync_table_exists(self, table_name: str) -> bool:
        """Check if a table exists. Blocks until complete.

        Args:
            table_name: Name of the table to check.

        Returns:
            True if table exists, False otherwise.

        Example:
            if client.sync_table_exists("users"):
                print("Table exists")
        """
        return self._client.sync_table_exists(table_name)  # type: ignore[attr-defined, no-any-return]

    def sync_delete_table(self, table_name: str) -> None:
        """Delete a table. Blocks until complete.

        Args:
            table_name: Name of the table to delete.

        Example:
            client.sync_delete_table("users")
        """
        self._client.sync_delete_table(table_name)  # type: ignore[attr-defined]

    def sync_wait_for_table_active(
        self,
        table_name: str,
        timeout_seconds: int | None = None,
    ) -> None:
        """Wait for a table to become active. Blocks until complete.

        Args:
            table_name: Name of the table to wait for.
            timeout_seconds: Maximum time to wait (default: 60).

        Example:
            client.sync_wait_for_table_active("users")
        """
        self._client.sync_wait_for_table_active(  # type: ignore[attr-defined]
            table_name, timeout_seconds=timeout_seconds
        )
