"""Query, scan, count, and parallel scan operations."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, TypeVar

from pydynox._internal._results import (
    AsyncModelQueryResult,
    AsyncModelScanResult,
    ModelQueryResult,
    ModelScanResult,
)
from pydynox.hooks import HookType

if TYPE_CHECKING:
    from pydynox._internal._metrics import OperationMetrics
    from pydynox.conditions import Condition
    from pydynox.model import Model

M = TypeVar("M", bound="Model")


def query(
    cls: type[M],
    hash_key: Any,
    range_key_condition: Condition | None = None,
    filter_condition: Condition | None = None,
    limit: int | None = None,
    scan_index_forward: bool = True,
    consistent_read: bool | None = None,
    last_evaluated_key: dict[str, Any] | None = None,
    as_dict: bool = False,
) -> ModelQueryResult[M]:
    """Query items by hash key with optional conditions.

    Args:
        hash_key: The hash key value to query.
        range_key_condition: Optional condition on the range key.
        filter_condition: Optional filter on non-key attributes.
        limit: Max items per page.
        scan_index_forward: Sort order. True = ascending, False = descending.
        consistent_read: If True, use strongly consistent read.
        last_evaluated_key: Start key for pagination.
        as_dict: If True, return dicts instead of Model instances.

    Returns:
        ModelQueryResult that yields typed model instances or dicts.
    """
    return ModelQueryResult(
        model_class=cls,
        hash_key_value=hash_key,
        range_key_condition=range_key_condition,
        filter_condition=filter_condition,
        limit=limit,
        scan_index_forward=scan_index_forward,
        consistent_read=consistent_read,
        last_evaluated_key=last_evaluated_key,
        as_dict=as_dict,
    )


def scan(
    cls: type[M],
    filter_condition: Condition | None = None,
    limit: int | None = None,
    consistent_read: bool | None = None,
    last_evaluated_key: dict[str, Any] | None = None,
    segment: int | None = None,
    total_segments: int | None = None,
    as_dict: bool = False,
) -> ModelScanResult[M]:
    """Scan all items in the table.

    Warning: Scan reads every item in the table. Use query() when possible.

    Args:
        filter_condition: Optional filter on attributes.
        limit: Max items per page.
        consistent_read: If True, use strongly consistent read.
        last_evaluated_key: Start key for pagination.
        segment: Segment number for parallel scan (0 to total_segments-1).
        total_segments: Total number of segments for parallel scan.
        as_dict: If True, return dicts instead of Model instances.

    Returns:
        ModelScanResult that yields typed model instances or dicts.

    Example:
        >>> for user in User.scan():
        ...     print(user.name)
        >>>
        >>> # With filter
        >>> for user in User.scan(filter_condition=User.age >= 18):
        ...     print(user.name)
    """
    return ModelScanResult(
        model_class=cls,
        filter_condition=filter_condition,
        limit=limit,
        consistent_read=consistent_read,
        last_evaluated_key=last_evaluated_key,
        segment=segment,
        total_segments=total_segments,
        as_dict=as_dict,
    )


def count(
    cls: type[M],
    filter_condition: Condition | None = None,
    consistent_read: bool | None = None,
) -> tuple[int, OperationMetrics]:
    """Count items in the table.

    Warning: Count scans the entire table. Use sparingly.

    Args:
        filter_condition: Optional filter on attributes.
        consistent_read: If True, use strongly consistent read.

    Returns:
        Tuple of (count, metrics).

    Example:
        >>> count, metrics = User.count()
        >>> print(f"Total users: {count}")
    """
    client = cls._get_client()
    table = cls._get_table()

    names: dict[str, str] = {}
    values: dict[str, Any] = {}

    filter_expr = None
    if filter_condition is not None:
        filter_expr = filter_condition.serialize(names, values)

    attr_names = {v: k for k, v in names.items()}

    use_consistent = consistent_read
    if use_consistent is None:
        use_consistent = getattr(cls.model_config, "consistent_read", False)

    return client.count(
        table,
        filter_expression=filter_expr,
        expression_attribute_names=attr_names if attr_names else None,
        expression_attribute_values=values if values else None,
        consistent_read=use_consistent,
    )


def execute_statement(
    cls: type[M],
    statement: str,
    parameters: list[Any] | None = None,
    consistent_read: bool = False,
) -> list[M]:
    """Execute a PartiQL statement and return typed model instances."""
    client = cls._get_client()
    result = client.execute_statement(
        statement,
        parameters=parameters,
        consistent_read=consistent_read,
    )
    return [cls.from_dict(item) for item in result]


# ========== ASYNC METHODS ==========


def async_query(
    cls: type[M],
    hash_key: Any,
    range_key_condition: Condition | None = None,
    filter_condition: Condition | None = None,
    limit: int | None = None,
    scan_index_forward: bool = True,
    consistent_read: bool | None = None,
    last_evaluated_key: dict[str, Any] | None = None,
    as_dict: bool = False,
) -> AsyncModelQueryResult[M]:
    """Async version of query."""
    return AsyncModelQueryResult(
        model_class=cls,
        hash_key_value=hash_key,
        range_key_condition=range_key_condition,
        filter_condition=filter_condition,
        limit=limit,
        scan_index_forward=scan_index_forward,
        consistent_read=consistent_read,
        last_evaluated_key=last_evaluated_key,
        as_dict=as_dict,
    )


def async_scan(
    cls: type[M],
    filter_condition: Condition | None = None,
    limit: int | None = None,
    consistent_read: bool | None = None,
    last_evaluated_key: dict[str, Any] | None = None,
    segment: int | None = None,
    total_segments: int | None = None,
    as_dict: bool = False,
) -> AsyncModelScanResult[M]:
    """Async version of scan."""
    return AsyncModelScanResult(
        model_class=cls,
        filter_condition=filter_condition,
        limit=limit,
        consistent_read=consistent_read,
        last_evaluated_key=last_evaluated_key,
        segment=segment,
        total_segments=total_segments,
        as_dict=as_dict,
    )


async def async_count(
    cls: type[M],
    filter_condition: Condition | None = None,
    consistent_read: bool | None = None,
) -> tuple[int, OperationMetrics]:
    """Async version of count."""
    client = cls._get_client()
    table = cls._get_table()

    names: dict[str, str] = {}
    values: dict[str, Any] = {}

    filter_expr = None
    if filter_condition is not None:
        filter_expr = filter_condition.serialize(names, values)

    attr_names = {v: k for k, v in names.items()}

    use_consistent = consistent_read
    if use_consistent is None:
        use_consistent = getattr(cls.model_config, "consistent_read", False)

    result = await client.async_count(
        table,
        filter_expression=filter_expr,
        expression_attribute_names=attr_names if attr_names else None,
        expression_attribute_values=values if values else None,
        consistent_read=use_consistent,
    )
    return result


async def async_execute_statement(
    cls: type[M],
    statement: str,
    parameters: list[Any] | None = None,
    consistent_read: bool = False,
) -> list[M]:
    """Async version of execute_statement."""
    client = cls._get_client()
    result = await client.async_execute_statement(
        statement,
        parameters=parameters,
        consistent_read=consistent_read,
    )
    return [cls.from_dict(item) for item in result]


# ========== PARALLEL SCAN ==========


def parallel_scan(
    cls: type[M],
    total_segments: int,
    filter_condition: Condition | None = None,
    consistent_read: bool | None = None,
    as_dict: bool = False,
) -> tuple[list[M] | list[dict[str, Any]], OperationMetrics]:
    """Parallel scan - runs multiple segment scans concurrently.

    Much faster than regular scan for large tables. Each segment is
    scanned in parallel using tokio tasks in Rust.

    Warning: Returns all items at once. For very large tables, consider
    using regular scan() with segment/total_segments for streaming.

    Args:
        total_segments: Number of parallel segments (1-1000000).
                       More segments = more parallelism, but more overhead.
                       Good starting point: 4-8 for most tables.
        filter_condition: Optional filter on attributes.
        consistent_read: If True, use strongly consistent read.
        as_dict: If True, return dicts instead of Model instances.

    Returns:
        Tuple of (list of model instances or dicts, metrics).

    Example:
        >>> users, metrics = User.parallel_scan(total_segments=4)
        >>> print(f"Found {len(users)} users in {metrics.duration_ms:.2f}ms")
        >>>
        >>> # With filter
        >>> active, metrics = User.parallel_scan(
        ...     total_segments=4,
        ...     filter_condition=User.status == "active"
        ... )
    """
    client = cls._get_client()
    table = cls._get_table()

    names: dict[str, str] = {}
    values: dict[str, Any] = {}

    filter_expr = None
    if filter_condition is not None:
        filter_expr = filter_condition.serialize(names, values)

    attr_names = {v: k for k, v in names.items()}

    use_consistent = consistent_read
    if use_consistent is None:
        use_consistent = getattr(cls.model_config, "consistent_read", False)

    items, metrics = client.parallel_scan(
        table,
        total_segments,
        filter_expression=filter_expr,
        expression_attribute_names=attr_names if attr_names else None,
        expression_attribute_values=values if values else None,
        consistent_read=use_consistent,
    )

    if as_dict:
        return items, metrics

    instances = [cls.from_dict(item) for item in items]

    skip = cls.model_config.skip_hooks if hasattr(cls, "model_config") else False
    if not skip:
        for instance in instances:
            instance._run_hooks(HookType.AFTER_LOAD)

    return instances, metrics


async def async_parallel_scan(
    cls: type[M],
    total_segments: int,
    filter_condition: Condition | None = None,
    consistent_read: bool | None = None,
    as_dict: bool = False,
) -> tuple[list[M] | list[dict[str, Any]], OperationMetrics]:
    """Async parallel scan - runs multiple segment scans concurrently.

    Much faster than regular scan for large tables. Each segment is
    scanned in parallel using tokio tasks in Rust.

    Warning: Returns all items at once. For very large tables, consider
    using regular async_scan() with segment/total_segments for streaming.

    Args:
        total_segments: Number of parallel segments (1-1000000).
                       More segments = more parallelism, but more overhead.
                       Good starting point: 4-8 for most tables.
        filter_condition: Optional filter on attributes.
        consistent_read: If True, use strongly consistent read.
        as_dict: If True, return dicts instead of Model instances.

    Returns:
        Tuple of (list of model instances or dicts, metrics).

    Example:
        >>> users, metrics = await User.async_parallel_scan(total_segments=4)
        >>> print(f"Found {len(users)} users in {metrics.duration_ms:.2f}ms")
    """
    client = cls._get_client()
    table = cls._get_table()

    names: dict[str, str] = {}
    values: dict[str, Any] = {}

    filter_expr = None
    if filter_condition is not None:
        filter_expr = filter_condition.serialize(names, values)

    attr_names = {v: k for k, v in names.items()}

    use_consistent = consistent_read
    if use_consistent is None:
        use_consistent = getattr(cls.model_config, "consistent_read", False)

    items, metrics = await client.async_parallel_scan(
        table,
        total_segments,
        filter_expression=filter_expr,
        expression_attribute_names=attr_names if attr_names else None,
        expression_attribute_values=values if values else None,
        consistent_read=use_consistent,
    )

    if as_dict:
        return items, metrics

    instances = [cls.from_dict(item) for item in items]

    skip = cls.model_config.skip_hooks if hasattr(cls, "model_config") else False
    if not skip:
        for instance in instances:
            instance._run_hooks(HookType.AFTER_LOAD)

    return instances, metrics
