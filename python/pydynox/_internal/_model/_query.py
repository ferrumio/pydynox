"""Query, scan, count, and parallel scan operations."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol, TypeVar

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


class _TemplateAttr(Protocol):
    """Protocol for attributes with template support."""

    has_template: bool
    placeholders: list[str]

    def build_key(self, values: dict[str, Any]) -> str: ...


def _resolve_hash_key(cls: type[M], hash_key: Any | None, kwargs: dict[str, Any]) -> Any:
    """Resolve hash key value, building from template if needed.

    If hash_key is provided directly, use it.
    Otherwise, check if the hash key attribute has a template and build from kwargs.
    """
    if hash_key is not None:
        return hash_key

    # Check if hash key has template
    if cls._hash_key is None:
        raise ValueError(f"Model {cls.__name__} has no hash_key defined")

    hash_attr = cls._attributes.get(cls._hash_key)
    if hash_attr is None:
        raise ValueError(f"Hash key attribute {cls._hash_key} not found")

    # If no template, can't build from kwargs
    if not (hasattr(hash_attr, "has_template") and hash_attr.has_template):
        raise ValueError(f"hash_key is required. Model {cls.__name__} hash key has no template.")

    # Cast to template protocol for type checker
    tattr: _TemplateAttr = hash_attr  # type: ignore[assignment]

    # Build from template using kwargs
    values = {}
    for placeholder in tattr.placeholders:
        if placeholder not in kwargs:
            raise ValueError(f"Missing value for template placeholder: {placeholder}")
        values[placeholder] = kwargs[placeholder]

    return tattr.build_key(values)


# ========== SYNC METHODS ==========


def sync_query(
    cls: type[M],
    hash_key: Any = None,
    range_key_condition: Condition | None = None,
    filter_condition: Condition | None = None,
    limit: int | None = None,
    page_size: int | None = None,
    scan_index_forward: bool = True,
    consistent_read: bool | None = None,
    last_evaluated_key: dict[str, Any] | None = None,
    as_dict: bool = False,
    fields: list[str] | None = None,
    **kwargs: Any,
) -> ModelQueryResult[M]:
    """Query items by hash key with optional conditions (sync).

    The hash_key can be provided directly or built from template placeholders.

    Examples:
        # Direct hash key
        Order.sync_query(hash_key="USER#123")

        # Using template placeholders (if pk has template="USER#{user_id}")
        Order.sync_query(user_id="123")
    """
    resolved_hash_key = _resolve_hash_key(cls, hash_key, kwargs)

    return ModelQueryResult(
        model_class=cls,
        hash_key_value=resolved_hash_key,
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
    hash_key: Any = None,
    range_key_condition: Condition | None = None,
    filter_condition: Condition | None = None,
    limit: int | None = None,
    page_size: int | None = None,
    scan_index_forward: bool = True,
    consistent_read: bool | None = None,
    last_evaluated_key: dict[str, Any] | None = None,
    as_dict: bool = False,
    fields: list[str] | None = None,
    **kwargs: Any,
) -> AsyncModelQueryResult[M]:
    """Query items by hash key with optional conditions (async, default).

    The hash_key can be provided directly or built from template placeholders.

    Examples:
        # Direct hash key
        async for order in Order.query(hash_key="USER#123"):
            print(order)

        # Using template placeholders (if pk has template="USER#{user_id}")
        async for order in Order.query(user_id="123"):
            print(order)
    """
    resolved_hash_key = _resolve_hash_key(cls, hash_key, kwargs)

    return AsyncModelQueryResult(
        model_class=cls,
        hash_key_value=resolved_hash_key,
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
