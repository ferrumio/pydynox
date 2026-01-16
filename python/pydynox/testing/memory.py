"""In-memory backend for testing pydynox without DynamoDB."""

from __future__ import annotations

import copy
import re
import time
from contextlib import contextmanager
from dataclasses import dataclass
from functools import wraps
from typing import Any, Callable, Iterator, TypeVar

from pydynox.config import clear_default_client, get_default_client, set_default_client


@dataclass
class FakeMetrics:
    """Fake metrics for in-memory backend."""

    duration_ms: float = 0.0
    consumed_rcu: float = 0.0
    consumed_wcu: float = 0.0
    request_id: str = "memory-backend"
    scanned_count: int = 0
    count: int = 0
    items_count: int = 0


@dataclass
class FakeTotalMetrics:
    """Fake total metrics for in-memory backend."""

    total_rcu: float = 0.0
    total_wcu: float = 0.0
    total_duration_ms: float = 0.0
    operation_count: int = 0
    get_count: int = 0
    put_count: int = 0
    delete_count: int = 0
    update_count: int = 0
    query_count: int = 0
    scan_count: int = 0

    def add(self, metrics: FakeMetrics, operation: str) -> None:
        """Add metrics from an operation."""
        self.total_rcu += metrics.consumed_rcu
        self.total_wcu += metrics.consumed_wcu
        self.total_duration_ms += metrics.duration_ms
        self.operation_count += 1

        if operation == "get":
            self.get_count += 1
        elif operation == "put":
            self.put_count += 1
        elif operation == "delete":
            self.delete_count += 1
        elif operation == "update":
            self.update_count += 1
        elif operation == "query":
            self.query_count += 1
        elif operation == "scan":
            self.scan_count += 1

    def reset(self) -> None:
        """Reset all metrics to zero."""
        self.total_rcu = 0.0
        self.total_wcu = 0.0
        self.total_duration_ms = 0.0
        self.operation_count = 0
        self.get_count = 0
        self.put_count = 0
        self.delete_count = 0
        self.update_count = 0
        self.query_count = 0
        self.scan_count = 0


F = TypeVar("F", bound=Callable[..., Any])


class MemoryBackend:
    """In-memory backend for testing pydynox code.

    Stores data in Python dicts. No external dependencies needed.
    Supports basic CRUD operations, queries, and scans.

    Example:
        >>> from pydynox.testing import MemoryBackend
        >>>
        >>> # As context manager
        >>> with MemoryBackend():
        ...     user = User(pk="USER#1", name="John")
        ...     user.save()
        ...     found = User.get(pk="USER#1")
        ...     assert found.name == "John"
        >>>
        >>> # As decorator
        >>> @MemoryBackend()
        ... def test_user_crud():
        ...     user = User(pk="USER#1", name="John")
        ...     user.save()
        ...     assert User.get(pk="USER#1") is not None
        >>>
        >>> # With seed data
        >>> with MemoryBackend(seed={"users": [{"pk": "USER#1", "name": "John"}]}):
        ...     user = User.get(pk="USER#1")
        ...     assert user.name == "John"
    """

    def __init__(self, seed: dict[str, list[dict[str, Any]]] | None = None) -> None:
        """Initialize the memory backend.

        Args:
            seed: Optional dict of table_name -> list of items to pre-populate.
        """
        self._seed = seed or {}
        self._previous_client: Any = None
        self._client: MemoryClient | None = None

    def __enter__(self) -> "MemoryBackend":
        """Enter context manager."""
        self._previous_client = get_default_client()
        self._client = MemoryClient(seed=self._seed)
        # Clear cached clients so models use the new MemoryClient
        self._clear_model_caches()
        set_default_client(self._client)  # type: ignore[arg-type]
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Exit context manager and restore previous client."""
        # Clear cached clients from all Model subclasses
        self._clear_model_caches()

        if self._previous_client is not None:
            set_default_client(self._previous_client)
        else:
            clear_default_client()
        self._client = None

    def _clear_model_caches(self) -> None:
        """Clear _client_instance cache from all Model subclasses."""
        from pydynox.model import Model

        for subclass in Model.__subclasses__():
            if hasattr(subclass, "_client_instance"):
                subclass._client_instance = None
            # Also clear nested subclasses
            for nested in subclass.__subclasses__():
                if hasattr(nested, "_client_instance"):
                    nested._client_instance = None

    def __call__(self, func: F) -> F:
        """Use as decorator."""

        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            with self:
                return func(*args, **kwargs)

        return wrapper  # type: ignore[return-value]

    @property
    def tables(self) -> dict[str, dict[str, dict[str, Any]]]:
        """Access the in-memory tables for inspection.

        Returns:
            Dict of table_name -> {key -> item}.
        """
        if self._client is None:
            return {}
        return self._client._tables

    def clear(self) -> None:
        """Clear all data from all tables."""
        if self._client is not None:
            self._client._tables.clear()


@contextmanager
def memory_backend(
    seed: dict[str, list[dict[str, Any]]] | None = None,
) -> Iterator[MemoryBackend]:
    """Context manager for in-memory testing.

    Args:
        seed: Optional dict of table_name -> list of items to pre-populate.

    Yields:
        MemoryBackend instance.

    Example:
        >>> with memory_backend() as backend:
        ...     user = User(pk="USER#1", name="John")
        ...     user.save()
        ...     assert "users" in backend.tables
    """
    backend = MemoryBackend(seed=seed)
    with backend:
        yield backend


class MemoryClient:
    """In-memory client that mimics DynamoDBClient interface."""

    def __init__(self, seed: dict[str, list[dict[str, Any]]] | None = None) -> None:
        # tables[table_name][key_string] = item
        self._tables: dict[str, dict[str, dict[str, Any]]] = {}
        self._table_schemas: dict[str, dict[str, str]] = {}  # table -> {hash_key, range_key}
        self._rate_limit = None
        self._diagnostics = None
        self._last_metrics: FakeMetrics | None = None
        self._total_metrics = FakeTotalMetrics()
        # For compatibility with code that accesses _client directly
        self._client = self

        # Load seed data
        if seed:
            for table_name, items in seed.items():
                self._tables[table_name] = {}
                for item in items:
                    # Infer key from first item
                    key_str = self._make_key_string(item)
                    self._tables[table_name][key_str] = copy.deepcopy(item)

    @property
    def diagnostics(self) -> None:
        """Return None - no diagnostics for memory backend."""
        return self._diagnostics

    @property
    def rate_limit(self) -> None:
        """Return None - no rate limiting for memory backend."""
        return self._rate_limit

    def _acquire_rcu(self, rcu: float = 1.0) -> None:
        """No-op for memory backend."""
        pass

    def _acquire_wcu(self, wcu: float = 1.0) -> None:
        """No-op for memory backend."""
        pass

    def _on_throttle(self) -> None:
        """No-op for memory backend."""
        pass

    def _record_write(self, table: str, pk: str) -> None:
        """No-op for memory backend."""
        pass

    def _record_read(self, table: str, pk: str) -> None:
        """No-op for memory backend."""
        pass

    def _make_key_string(self, item_or_key: dict[str, Any]) -> str:
        """Create a unique key string from item or key dict.

        Uses only pk and sk fields (if present) to create consistent keys.
        """
        pk = item_or_key.get("pk", "")
        sk = item_or_key.get("sk", "")

        # Also check for common key patterns
        if not pk:
            # Try to find hash_key by looking for common patterns
            for key in ["pk", "PK", "hash_key", "id", "short_code"]:
                if key in item_or_key:
                    pk = item_or_key[key]
                    break

        if pk and sk:
            return f"{pk}|{sk}"
        return str(pk)

    def _get_table(self, table: str) -> dict[str, dict[str, Any]]:
        """Get or create table storage."""
        if table not in self._tables:
            self._tables[table] = {}
        return self._tables[table]

    def _make_metrics(self, start: float, rcu: float = 0, wcu: float = 0) -> FakeMetrics:
        """Create metrics object."""
        return FakeMetrics(
            duration_ms=(time.time() - start) * 1000,
            consumed_rcu=rcu,
            consumed_wcu=wcu,
            request_id="memory-backend",
        )

    def _record_metrics(self, metrics: FakeMetrics, operation: str) -> None:
        """Record metrics for an operation."""
        self._last_metrics = metrics
        self._total_metrics.add(metrics, operation)

    # ========== CRUD ==========

    def put_item(
        self,
        table: str,
        item: dict[str, Any],
        condition_expression: str | None = None,
        expression_attribute_names: dict[str, str] | None = None,
        expression_attribute_values: dict[str, Any] | None = None,
    ) -> FakeMetrics:
        """Put an item into the in-memory table."""
        start = time.time()
        tbl = self._get_table(table)
        key_str = self._make_key_string(item)

        # Check condition if provided
        if condition_expression:
            existing = tbl.get(key_str)
            if not self._check_condition(
                existing,
                condition_expression,
                expression_attribute_names,
                expression_attribute_values,
            ):
                from pydynox.exceptions import ConditionalCheckFailedException

                raise ConditionalCheckFailedException("Condition check failed")

        tbl[key_str] = copy.deepcopy(item)
        metrics = self._make_metrics(start, wcu=1)
        self._record_metrics(metrics, "put")
        return metrics

    def get_item(
        self, table: str, key: dict[str, Any], consistent_read: bool = False
    ) -> dict[str, Any] | None:
        """Get an item from the in-memory table."""
        start = time.time()
        tbl = self._get_table(table)
        key_str = self._make_key_string(key)
        item = tbl.get(key_str)
        metrics = self._make_metrics(start, rcu=1)
        self._record_metrics(metrics, "get")
        if item is None:
            return None
        return copy.deepcopy(item)

    def delete_item(
        self,
        table: str,
        key: dict[str, Any],
        condition_expression: str | None = None,
        expression_attribute_names: dict[str, str] | None = None,
        expression_attribute_values: dict[str, Any] | None = None,
    ) -> FakeMetrics:
        """Delete an item from the in-memory table."""
        start = time.time()
        tbl = self._get_table(table)
        key_str = self._make_key_string(key)

        # Check condition if provided
        if condition_expression:
            existing = tbl.get(key_str)
            if not self._check_condition(
                existing,
                condition_expression,
                expression_attribute_names,
                expression_attribute_values,
            ):
                from pydynox.exceptions import ConditionalCheckFailedException

                raise ConditionalCheckFailedException("Condition check failed")

        tbl.pop(key_str, None)
        metrics = self._make_metrics(start, wcu=1)
        self._record_metrics(metrics, "delete")
        return metrics

    def update_item(
        self,
        table: str,
        key: dict[str, Any],
        updates: dict[str, Any] | None = None,
        update_expression: str | None = None,
        condition_expression: str | None = None,
        expression_attribute_names: dict[str, str] | None = None,
        expression_attribute_values: dict[str, Any] | None = None,
    ) -> FakeMetrics:
        """Update an item in the in-memory table."""
        start = time.time()
        tbl = self._get_table(table)
        key_str = self._make_key_string(key)

        existing = tbl.get(key_str)

        # Check condition if provided
        if condition_expression:
            if not self._check_condition(
                existing,
                condition_expression,
                expression_attribute_names,
                expression_attribute_values,
            ):
                from pydynox.exceptions import ConditionalCheckFailedException

                raise ConditionalCheckFailedException("Condition check failed")

        # Create item if not exists
        if existing is None:
            existing = copy.deepcopy(key)
            tbl[key_str] = existing

        # Apply updates
        if updates:
            for attr, value in updates.items():
                existing[attr] = value

        # Apply update expression
        if update_expression:
            self._apply_update_expression(
                existing, update_expression, expression_attribute_names, expression_attribute_values
            )

        metrics = self._make_metrics(start, wcu=1)
        self._record_metrics(metrics, "update")
        return metrics

    # ========== QUERY/SCAN ==========

    def query_page(
        self,
        table: str,
        key_condition_expression: str,
        filter_expression: str | None = None,
        expression_attribute_names: dict[str, str] | None = None,
        expression_attribute_values: dict[str, Any] | None = None,
        limit: int | None = None,
        scan_index_forward: bool = True,
        consistent_read: bool = False,
        exclusive_start_key: dict[str, Any] | None = None,
        index_name: str | None = None,
        projection_expression: str | None = None,
    ) -> tuple[list[dict[str, Any]], dict[str, Any] | None, FakeMetrics]:
        """Query a page of items from the in-memory table."""
        result = self.query(
            table,
            key_condition_expression,
            filter_expression,
            expression_attribute_names,
            expression_attribute_values,
            limit,
            scan_index_forward,
            consistent_read,
            exclusive_start_key,
            index_name,
        )
        metrics = result["metrics"]
        metrics.items_count = len(result["items"])
        return result["items"], result["last_evaluated_key"], metrics

    def scan_page(
        self,
        table: str,
        filter_expression: str | None = None,
        expression_attribute_names: dict[str, str] | None = None,
        expression_attribute_values: dict[str, Any] | None = None,
        limit: int | None = None,
        consistent_read: bool = False,
        exclusive_start_key: dict[str, Any] | None = None,
        segment: int | None = None,
        total_segments: int | None = None,
        index_name: str | None = None,
        projection_expression: str | None = None,
    ) -> tuple[list[dict[str, Any]], dict[str, Any] | None, FakeMetrics]:
        """Scan a page of items from the in-memory table."""
        result = self.scan(
            table,
            filter_expression,
            expression_attribute_names,
            expression_attribute_values,
            limit,
            consistent_read,
            exclusive_start_key,
            segment,
            total_segments,
            index_name,
        )
        metrics = result["metrics"]
        metrics.items_count = len(result["items"])
        return result["items"], result["last_evaluated_key"], metrics

    def query(
        self,
        table: str,
        key_condition_expression: str,
        filter_expression: str | None = None,
        expression_attribute_names: dict[str, str] | None = None,
        expression_attribute_values: dict[str, Any] | None = None,
        limit: int | None = None,
        scan_index_forward: bool = True,
        consistent_read: bool = False,
        exclusive_start_key: dict[str, Any] | None = None,
        index_name: str | None = None,
    ) -> dict[str, Any]:
        """Query items from the in-memory table."""
        start = time.time()
        tbl = self._get_table(table)

        # Parse key condition to get hash key value
        items = []
        for item in tbl.values():
            if self._matches_key_condition(
                item,
                key_condition_expression,
                expression_attribute_names,
                expression_attribute_values,
            ):
                if filter_expression is None or self._check_condition(
                    item, filter_expression, expression_attribute_names, expression_attribute_values
                ):
                    items.append(copy.deepcopy(item))

        # Sort (simplified - just by first key)
        if not scan_index_forward:
            items.reverse()

        # Apply limit
        if limit and len(items) > limit:
            items = items[:limit]

        return {
            "items": items,
            "count": len(items),
            "scanned_count": len(items),
            "last_evaluated_key": None,
            "metrics": self._make_metrics(start, rcu=len(items) * 0.5),
        }

    def scan(
        self,
        table: str,
        filter_expression: str | None = None,
        expression_attribute_names: dict[str, str] | None = None,
        expression_attribute_values: dict[str, Any] | None = None,
        limit: int | None = None,
        consistent_read: bool = False,
        exclusive_start_key: dict[str, Any] | None = None,
        segment: int | None = None,
        total_segments: int | None = None,
        index_name: str | None = None,
    ) -> dict[str, Any]:
        """Scan all items from the in-memory table."""
        start = time.time()
        tbl = self._get_table(table)

        items = []
        for item in tbl.values():
            if filter_expression is None or self._check_condition(
                item, filter_expression, expression_attribute_names, expression_attribute_values
            ):
                items.append(copy.deepcopy(item))

        # Apply limit
        if limit and len(items) > limit:
            items = items[:limit]

        return {
            "items": items,
            "count": len(items),
            "scanned_count": len(tbl),
            "last_evaluated_key": None,
            "metrics": self._make_metrics(start, rcu=len(tbl) * 0.5),
        }

    # ========== BATCH ==========

    def batch_get_item(
        self,
        request_items: dict[str, dict[str, Any]],
    ) -> dict[str, Any]:
        """Batch get items from multiple tables."""
        start = time.time()
        responses: dict[str, list[dict[str, Any]]] = {}
        total_rcu = 0.0

        for table_name, request in request_items.items():
            keys = request.get("Keys", [])
            tbl = self._get_table(table_name)
            responses[table_name] = []

            for key in keys:
                key_str = self._make_key_string(key)
                item = tbl.get(key_str)
                if item:
                    responses[table_name].append(copy.deepcopy(item))
                    total_rcu += 1

        return {
            "Responses": responses,
            "UnprocessedKeys": {},
            "metrics": self._make_metrics(start, rcu=total_rcu),
        }

    def batch_write_item(
        self,
        request_items: dict[str, list[dict[str, Any]]],
    ) -> dict[str, Any]:
        """Batch write items to multiple tables."""
        start = time.time()
        total_wcu = 0.0

        for table_name, requests in request_items.items():
            tbl = self._get_table(table_name)

            for request in requests:
                if "PutRequest" in request:
                    item = request["PutRequest"]["Item"]
                    key_str = self._make_key_string(item)
                    tbl[key_str] = copy.deepcopy(item)
                    total_wcu += 1
                elif "DeleteRequest" in request:
                    key = request["DeleteRequest"]["Key"]
                    key_str = self._make_key_string(key)
                    tbl.pop(key_str, None)
                    total_wcu += 1

        return {
            "UnprocessedItems": {},
            "metrics": self._make_metrics(start, wcu=total_wcu),
        }

    # ========== TABLE ==========

    def table_exists(self, table: str) -> bool:
        """Check if table exists (always True for memory backend)."""
        return table in self._tables

    def create_table(self, table: str, **kwargs: Any) -> None:
        """Create a table (just initializes empty dict)."""
        if table not in self._tables:
            self._tables[table] = {}

    def delete_table(self, table: str) -> None:
        """Delete a table."""
        self._tables.pop(table, None)

    # ========== HELPERS ==========

    def get_region(self) -> str:
        """Return fake region."""
        return "us-east-1"

    def get_last_metrics(self) -> FakeMetrics | None:
        """Get metrics from the last operation."""
        return self._last_metrics

    def get_total_metrics(self) -> FakeTotalMetrics:
        """Get aggregated metrics from all operations."""
        return self._total_metrics

    def reset_metrics(self) -> None:
        """Reset all metrics to zero."""
        self._last_metrics = None
        self._total_metrics.reset()

    def ping(self) -> bool:
        """Always returns True for memory backend."""
        return True

    def _check_condition(
        self,
        item: dict[str, Any] | None,
        condition: str,
        attr_names: dict[str, str] | None,
        attr_values: dict[str, Any] | None,
    ) -> bool:
        """Check if item matches condition expression.

        Supports basic conditions:
        - attribute_exists(attr)
        - attribute_not_exists(attr)
        - attr = :value
        - attr <> :value
        - attr < :value
        - attr <= :value
        - attr > :value
        - attr >= :value
        """
        if item is None:
            # For attribute_not_exists, None item means condition passes
            if "attribute_not_exists" in condition:
                return True
            return False

        # Resolve attribute names
        resolved_condition = condition
        if attr_names:
            for placeholder, real_name in attr_names.items():
                resolved_condition = resolved_condition.replace(placeholder, real_name)

        # Check attribute_exists
        match = re.search(r"attribute_exists\((\w+)\)", resolved_condition)
        if match:
            attr = match.group(1)
            return attr in item

        # Check attribute_not_exists
        match = re.search(r"attribute_not_exists\((\w+)\)", resolved_condition)
        if match:
            attr = match.group(1)
            return attr not in item

        # Check comparisons
        for op, func in [
            ("=", lambda a, b: a == b),
            ("<>", lambda a, b: a != b),
            ("<=", lambda a, b: a <= b),
            (">=", lambda a, b: a >= b),
            ("<", lambda a, b: a < b),
            (">", lambda a, b: a > b),
        ]:
            match = re.search(rf"(\w+)\s*{re.escape(op)}\s*(:?\w+)", resolved_condition)
            if match:
                attr = match.group(1)
                value_key = match.group(2)
                if attr_values and value_key in attr_values:
                    expected = attr_values[value_key]
                    actual = item.get(attr)
                    return func(actual, expected)

        # Default: pass
        return True

    def _matches_key_condition(
        self,
        item: dict[str, Any],
        condition: str,
        attr_names: dict[str, str] | None,
        attr_values: dict[str, Any] | None,
    ) -> bool:
        """Check if item matches key condition expression.

        Supports:
        - pk = :value
        - pk = :value AND sk begins_with :prefix
        - pk = :value AND sk BETWEEN :start AND :end
        """
        # Resolve attribute names
        resolved = condition
        if attr_names:
            for placeholder, real_name in attr_names.items():
                resolved = resolved.replace(placeholder, real_name)

        # Split by AND
        parts = re.split(r"\s+AND\s+", resolved, flags=re.IGNORECASE)

        for part in parts:
            part = part.strip()

            # Check equality
            match = re.search(r"(\w+)\s*=\s*(:?\w+)", part)
            if match:
                attr = match.group(1)
                value_key = match.group(2)
                if attr_values and value_key in attr_values:
                    if item.get(attr) != attr_values[value_key]:
                        return False
                continue

            # Check begins_with
            match = re.search(r"begins_with\s*\(\s*(\w+)\s*,\s*(:?\w+)\s*\)", part, re.IGNORECASE)
            if match:
                attr = match.group(1)
                value_key = match.group(2)
                if attr_values and value_key in attr_values:
                    prefix = attr_values[value_key]
                    actual = item.get(attr, "")
                    if not str(actual).startswith(str(prefix)):
                        return False
                continue

            # Check BETWEEN
            match = re.search(r"(\w+)\s+BETWEEN\s+(:?\w+)\s+AND\s+(:?\w+)", part, re.IGNORECASE)
            if match:
                attr = match.group(1)
                start_key = match.group(2)
                end_key = match.group(3)
                if attr_values:
                    start_val = attr_values.get(start_key)
                    end_val = attr_values.get(end_key)
                    actual = item.get(attr)
                    if actual is None or not (start_val <= actual <= end_val):
                        return False
                continue

        return True

    def _apply_update_expression(
        self,
        item: dict[str, Any],
        expression: str,
        attr_names: dict[str, str] | None,
        attr_values: dict[str, Any] | None,
    ) -> None:
        """Apply update expression to item.

        Supports:
        - SET attr = :value
        - SET attr = attr + :value (ADD)
        - REMOVE attr
        """
        # Resolve attribute names
        resolved = expression
        if attr_names:
            for placeholder, real_name in attr_names.items():
                resolved = resolved.replace(placeholder, real_name)

        # Handle SET
        set_match = re.search(r"SET\s+(.+?)(?:REMOVE|ADD|DELETE|$)", resolved, re.IGNORECASE)
        if set_match:
            set_clause = set_match.group(1).strip()
            # Split by comma
            for assignment in set_clause.split(","):
                assignment = assignment.strip()
                if not assignment:
                    continue

                # Check for attr = attr + :value (increment)
                match = re.search(r"(\w+)\s*=\s*(\w+)\s*\+\s*(:?\w+)", assignment)
                if match:
                    attr = match.group(1)
                    value_key = match.group(3)
                    if attr_values and value_key in attr_values:
                        current = item.get(attr, 0)
                        item[attr] = current + attr_values[value_key]
                    continue

                # Check for attr = attr - :value (decrement)
                match = re.search(r"(\w+)\s*=\s*(\w+)\s*-\s*(:?\w+)", assignment)
                if match:
                    attr = match.group(1)
                    value_key = match.group(3)
                    if attr_values and value_key in attr_values:
                        current = item.get(attr, 0)
                        item[attr] = current - attr_values[value_key]
                    continue

                # Simple assignment: attr = :value
                match = re.search(r"(\w+)\s*=\s*(:?\w+)", assignment)
                if match:
                    attr = match.group(1)
                    value_key = match.group(2)
                    if attr_values and value_key in attr_values:
                        item[attr] = attr_values[value_key]

        # Handle REMOVE
        remove_match = re.search(r"REMOVE\s+(.+?)(?:SET|ADD|DELETE|$)", resolved, re.IGNORECASE)
        if remove_match:
            remove_clause = remove_match.group(1).strip()
            for attr in remove_clause.split(","):
                attr = attr.strip()
                if attr in item:
                    del item[attr]

        # Handle ADD (for numbers and sets)
        add_match = re.search(r"ADD\s+(\w+)\s+(:?\w+)", resolved, re.IGNORECASE)
        if add_match:
            attr = add_match.group(1)
            value_key = add_match.group(2)
            if attr_values and value_key in attr_values:
                add_value = attr_values[value_key]
                if isinstance(add_value, (int, float)):
                    item[attr] = item.get(attr, 0) + add_value
                elif isinstance(add_value, set):
                    current = item.get(attr, set())
                    item[attr] = current | add_value
