"""Hot partition detection for DynamoDB.

Example:
    >>> from pydynox import DynamoDBClient
    >>> from pydynox.diagnostics import HotPartitionDetector
    >>>
    >>> detector = HotPartitionDetector(
    ...     writes_threshold=500,
    ...     reads_threshold=1500,
    ...     window_seconds=60,
    ... )
    >>>
    >>> client = DynamoDBClient(diagnostics=detector)
"""

from __future__ import annotations

import logging
from typing import Any

from pydynox import pydynox_core

logger = logging.getLogger("pydynox.diagnostics")


class HotPartitionDetector:
    """Detects hot partitions by tracking partition key access.

    DynamoDB partitions have limits (~1000 WCU/s, ~3000 RCU/s per partition).
    This detector warns when a single partition key gets too much traffic.

    Args:
        writes_threshold: Max writes per minute before warning.
        reads_threshold: Max reads per minute before warning.
        window_seconds: Sliding window in seconds.

    Example:
        >>> detector = HotPartitionDetector(
        ...     writes_threshold=500,
        ...     reads_threshold=1500,
        ...     window_seconds=60,
        ... )
        >>>
        >>> client = DynamoDBClient(diagnostics=detector)
        >>>
        >>> # After many writes to same pk...
        >>> # WARNING: Hot partition detected - table="events" pk="EVENTS" had 500 writes in 60s
    """

    _tracker: Any  # pydynox_core.HotPartitionTracker

    def __init__(
        self,
        writes_threshold: int,
        reads_threshold: int,
        window_seconds: int,
    ) -> None:
        self._tracker = pydynox_core.HotPartitionTracker(
            writes_threshold=writes_threshold,
            reads_threshold=reads_threshold,
            window_seconds=window_seconds,
        )
        self._writes_threshold = writes_threshold
        self._reads_threshold = reads_threshold
        self._window_seconds = window_seconds
        # Per-table overrides: table -> (writes_threshold, reads_threshold)
        self._table_overrides: dict[str, tuple[int | None, int | None]] = {}

    @property
    def writes_threshold(self) -> int:
        """Max writes per window before warning."""
        return self._writes_threshold

    @property
    def reads_threshold(self) -> int:
        """Max reads per window before warning."""
        return self._reads_threshold

    @property
    def window_seconds(self) -> int:
        """Sliding window in seconds."""
        return self._window_seconds

    def set_table_thresholds(
        self,
        table: str,
        writes_threshold: int | None = None,
        reads_threshold: int | None = None,
    ) -> None:
        """Set custom thresholds for a specific table.

        Args:
            table: Table name.
            writes_threshold: Override writes threshold for this table.
            reads_threshold: Override reads threshold for this table.
        """
        self._table_overrides[table] = (writes_threshold, reads_threshold)

    def _get_writes_threshold(self, table: str) -> int:
        """Get writes threshold for a table (with override support)."""
        if table in self._table_overrides:
            override = self._table_overrides[table][0]
            if override is not None:
                return override
        return self._writes_threshold

    def _get_reads_threshold(self, table: str) -> int:
        """Get reads threshold for a table (with override support)."""
        if table in self._table_overrides:
            override = self._table_overrides[table][1]
            if override is not None:
                return override
        return self._reads_threshold

    def record_write(self, table: str, pk: str) -> None:
        """Record a write operation and warn if hot.

        Args:
            table: Table name.
            pk: Partition key value.
        """
        # Always record in tracker
        self._tracker.record_write(table, pk)

        # Check against threshold (with override support)
        count: int = self._tracker.get_write_count(table, pk)
        threshold = self._get_writes_threshold(table)
        if count >= threshold:
            logger.warning(
                'Hot partition detected - table="%s" pk="%s" had %d writes in %ds',
                table,
                pk,
                count,
                self._window_seconds,
            )

    def record_read(self, table: str, pk: str) -> None:
        """Record a read operation and warn if hot.

        Args:
            table: Table name.
            pk: Partition key value.
        """
        # Always record in tracker
        self._tracker.record_read(table, pk)

        # Check against threshold (with override support)
        count: int = self._tracker.get_read_count(table, pk)
        threshold = self._get_reads_threshold(table)
        if count >= threshold:
            logger.warning(
                'Hot partition detected - table="%s" pk="%s" had %d reads in %ds',
                table,
                pk,
                count,
                self._window_seconds,
            )

    def get_write_count(self, table: str, pk: str) -> int:
        """Get current write count for a partition key.

        Args:
            table: Table name.
            pk: Partition key value.

        Returns:
            Number of writes in the current window.
        """
        count: int = self._tracker.get_write_count(table, pk)
        return count

    def get_read_count(self, table: str, pk: str) -> int:
        """Get current read count for a partition key.

        Args:
            table: Table name.
            pk: Partition key value.

        Returns:
            Number of reads in the current window.
        """
        count: int = self._tracker.get_read_count(table, pk)
        return count

    def clear(self) -> None:
        """Clear all tracked entries."""
        self._tracker.clear()
        self._table_overrides.clear()
