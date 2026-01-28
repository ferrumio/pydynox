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


# ========== SYNC METHODS ==========


def sync_query(
    cls: type[M],
    hash_key: Any,
    range_key_condition: Condition | None = None,
    filter_condition: Condition | None = None,
    limit: int | None = None,
    page_size: int | None = None,
    scan_index_forward: bool = True,
    consistent_read: bool | None = None,
    last_evaluated_key: dict[str, Any] | None = None,
    as_dict: bool = False,
    fields: list[str] | None = None,
) -> ModelQueryResult[M]:
    """Query items by hash key with optional conditions (sync)."""
    return ModelQueryResult(
        model_class=cls,
        hash_key_value=hash_key,
        range_key_condition=range_key_condition,
        filter_condition=filter_condition,
        limit=limit,
        page_size=page_size,
        scan_index_forward=scan_index_forward,
        consistent_read=consistent_read,
        last_evaluated_key=last_evaluated_key,
        as_dict=as_dict,
        fields=fields,
    )


def sync_scan(
    cls: type[M],
    filter_condition: Condition | None = None,
    limit: int | None = None,
    page_size: int | None = None,
    consistent_read: bool | None = None,
    last_evaluated_key: dict[str, Any] | None = None,
    segment: int | None = None,
    total_segments: int | None = None,
    as_dict: bool = False,
    fields: list[str] | None = None,
) -> ModelScanResult[M]:
    """Scan all items in the table (sync)."""
    return ModelScanResult(
        model_class=cls,
        filter_condition=filter_condition,
        limit=limit,
        page_size=page_size,
        consistent_read=consistent_read,
        last_evaluated_key=last_evaluated_key,
        segment=segment,
        total_segments=total_segments,
        as_dict=as_dict,
        fields=fields,
    )


def sync_count(
    cls: type[M],
    filter_condition: Condition | None = None,
    consistent_read: bool | None = None,
) -> tuple[int, OperationMetrics]:
    """Count items in the table (sync)."""
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

    return client.sync_count(
        table,
        filter_expression=filter_expr,
        expression_attribute_names=attr_names if attr_names else None,
        expression_attribute_values=values if values else None,
        consistent_read=use_consistent,
    )


def sync_execute_statement(
    cls: type[M],
    statement: str,
    parameters: list[Any] | None = None,
    consistent_read: bool = False,
) -> list[M]:
    """Execute a PartiQL statement (sync)."""
    client = cls._get_client()
    result = client.sync_execute_statement(
        statement,
        parameters=parameters,
        consistent_read=consistent_read,
    )
    return [cls.from_dict(item) for item in result]


def sync_parallel_scan(
    cls: type[M],
    total_segments: int,
    filter_condition: Condition | None = None,
    consistent_read: bool | None = None,
    as_dict: bool = False,
) -> tuple[list[M] | list[dict[str, Any]], OperationMetrics]:
    """Parallel scan (sync)."""
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

    items, metrics = client.sync_parallel_scan(
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


# ========== ASYNC METHODS (default) ==========


def query(
    cls: type[M],
    hash_key: Any,
    range_key_condition: Condition | None = None,
    filter_condition: Condition | None = None,
    limit: int | None = None,
    page_size: int | None = None,
    scan_index_forward: bool = True,
    consistent_read: bool | None = None,
    last_evaluated_key: dict[str, Any] | None = None,
    as_dict: bool = False,
    fields: list[str] | None = None,
) -> AsyncModelQueryResult[M]:
    """Query items by hash key with optional conditions (async, default)."""
    return AsyncModelQueryResult(
        model_class=cls,
        hash_key_value=hash_key,
        range_key_condition=range_key_condition,
        filter_condition=filter_condition,
        limit=limit,
        page_size=page_size,
        scan_index_forward=scan_index_forward,
        consistent_read=consistent_read,
        last_evaluated_key=last_evaluated_key,
        as_dict=as_dict,
        fields=fields,
    )


def scan(
    cls: type[M],
    filter_condition: Condition | None = None,
    limit: int | None = None,
    page_size: int | None = None,
    consistent_read: bool | None = None,
    last_evaluated_key: dict[str, Any] | None = None,
    segment: int | None = None,
    total_segments: int | None = None,
    as_dict: bool = False,
    fields: list[str] | None = None,
) -> AsyncModelScanResult[M]:
    """Scan all items in the table (async, default)."""
    return AsyncModelScanResult(
        model_class=cls,
        filter_condition=filter_condition,
        limit=limit,
        page_size=page_size,
        consistent_read=consistent_read,
        last_evaluated_key=last_evaluated_key,
        segment=segment,
        total_segments=total_segments,
        as_dict=as_dict,
        fields=fields,
    )


async def count(
    cls: type[M],
    filter_condition: Condition | None = None,
    consistent_read: bool | None = None,
) -> tuple[int, OperationMetrics]:
    """Count items in the table (async, default)."""
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

    return await client.count(
        table,
        filter_expression=filter_expr,
        expression_attribute_names=attr_names if attr_names else None,
        expression_attribute_values=values if values else None,
        consistent_read=use_consistent,
    )


async def execute_statement(
    cls: type[M],
    statement: str,
    parameters: list[Any] | None = None,
    consistent_read: bool = False,
) -> list[M]:
    """Execute a PartiQL statement (async, default)."""
    client = cls._get_client()
    result = await client.execute_statement(
        statement,
        parameters=parameters,
        consistent_read=consistent_read,
    )
    return [cls.from_dict(item) for item in result]


async def parallel_scan(
    cls: type[M],
    total_segments: int,
    filter_condition: Condition | None = None,
    consistent_read: bool | None = None,
    as_dict: bool = False,
) -> tuple[list[M] | list[dict[str, Any]], OperationMetrics]:
    """Parallel scan (async, default)."""
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

    items, metrics = await client.parallel_scan(
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
