"""Batch operations for DynamoDB."""

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pydynox.client import DynamoDBClient


class BatchWriter:
    """Context manager for batch write operations.

    Collects put and delete operations, then sends them all at once
    when the context exits. Handles splitting into batches of 25 items
    and retrying unprocessed items.

    Example:
        >>> with BatchWriter(client, "users") as batch:
        ...     batch.put({"pk": "USER#1", "sk": "PROFILE", "name": "Alice"})
        ...     batch.put({"pk": "USER#2", "sk": "PROFILE", "name": "Bob"})
        ...     batch.delete({"pk": "USER#3", "sk": "PROFILE"})
    """

    def __init__(self, client: "DynamoDBClient", table: str):
        """Create a BatchWriter.

        Args:
            client: The DynamoDBClient to use.
            table: The table name.
        """
        self._client = client
        self._table = table
        self._put_items: list[dict[str, Any]] = []
        self._delete_keys: list[dict[str, Any]] = []

    def __enter__(self) -> "BatchWriter":
        """Enter the context manager."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit the context manager and send all operations."""
        if exc_type is None:
            self.flush()

    def put(self, item: dict[str, Any]) -> None:
        """Add an item to be put.

        Args:
            item: The item to put (as a dict).
        """
        self._put_items.append(item)

    def delete(self, key: dict[str, Any]) -> None:
        """Add a key to be deleted.

        Args:
            key: The key to delete (as a dict with pk and optional sk).
        """
        self._delete_keys.append(key)

    def flush(self) -> None:
        """Send all collected operations to DynamoDB.

        Called automatically when exiting the context manager.
        Can also be called manually to send operations early.
        """
        if not self._put_items and not self._delete_keys:
            return

        self._client.batch_write(
            self._table,
            put_items=self._put_items,
            delete_keys=self._delete_keys,
        )

        # Clear the lists after successful write
        self._put_items = []
        self._delete_keys = []
