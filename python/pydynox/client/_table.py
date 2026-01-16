"""Table management operations."""

from __future__ import annotations

from typing import Any


class TableOperations:
    """Table management operations: create, delete, exists, wait."""

    def create_table(
        self,
        table_name: str,
        hash_key: tuple[str, str],
        range_key: tuple[str, str] | None = None,
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
        """Create a new DynamoDB table."""
        self._client.create_table(  # type: ignore[attr-defined]
            table_name,
            hash_key,
            range_key=range_key,
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

    def table_exists(self, table_name: str) -> bool:
        """Check if a table exists."""
        return self._client.table_exists(table_name)  # type: ignore[attr-defined, no-any-return]

    def delete_table(self, table_name: str) -> None:
        """Delete a table."""
        self._client.delete_table(table_name)  # type: ignore[attr-defined]

    def wait_for_table_active(
        self,
        table_name: str,
        timeout_seconds: int | None = None,
    ) -> None:
        """Wait for a table to become active."""
        self._client.wait_for_table_active(  # type: ignore[attr-defined]
            table_name, timeout_seconds=timeout_seconds
        )
