"""Model query and scan result classes."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Generic, TypeVar, Union

from pydynox.hooks import HookType
from pydynox.query import AsyncQueryResult, AsyncScanResult, QueryResult, ScanResult

if TYPE_CHECKING:
    from pydynox.conditions import Condition
    from pydynox.model import Model

M = TypeVar("M", bound="Model")

# Type alias for results that can be either Model or dict
ResultItem = Union[M, dict[str, Any]]


def _serialize_filter(
    condition: Condition | None, names: dict[str, str], values: dict[str, Any]
) -> str | None:
    """Serialize a filter condition. Returns None if no condition."""
    if condition is None:
        return None
    return condition.serialize(names, values)


def _get_consistent_read(model_class: type[M], explicit: bool | None) -> bool:
    """Get consistent_read value, falling back to model config."""
    if explicit is not None:
        return explicit
    return getattr(model_class.model_config, "consistent_read", False)


def _build_query_params(
    model_class: type[M],
    hash_key_value: Any,
    range_key_condition: Condition | None,
    filter_condition: Condition | None,
    consistent_read: bool | None,
    fields: list[str] | None = None,
) -> tuple[str, str | None, str | None, dict[str, str] | None, dict[str, Any] | None, bool]:
    """Build query expression params.

    Returns (key_cond, filter_expr, projection_expr, attr_names, attr_values, consistent).
    """
    hash_key_name = model_class._hash_key
    if hash_key_name is None:
        raise ValueError(f"Model {model_class.__name__} has no hash key defined")

    names: dict[str, str] = {}
    values: dict[str, Any] = {}

    # Build key condition
    hk_placeholder = "#pk"
    hk_val_placeholder = ":pkv"
    names[hash_key_name] = hk_placeholder
    values[hk_val_placeholder] = hash_key_value
    key_condition = f"{hk_placeholder} = {hk_val_placeholder}"

    if range_key_condition is not None:
        rk_expr = range_key_condition.serialize(names, values)
        key_condition = f"{key_condition} AND {rk_expr}"

    filter_expr = _serialize_filter(filter_condition, names, values)

    # Build projection expression
    projection_expr = None
    proj_names: dict[str, str] = {}
    if fields:
        proj_parts = []
        for i, field in enumerate(fields):
            parts = field.split(".")
            part_placeholders = []
            for part in parts:
                placeholder = f"#proj{i}_{len(part_placeholders)}"
                proj_names[placeholder] = part
                part_placeholders.append(placeholder)
            proj_parts.append(".".join(part_placeholders))
        projection_expr = ", ".join(proj_parts)

    # Merge names: conditions use {name: placeholder}, projection uses {placeholder: name}
    # Convert condition names to {placeholder: name} format and merge with projection
    attr_names = {v: k for k, v in names.items()}
    attr_names.update(proj_names)

    use_consistent = _get_consistent_read(model_class, consistent_read)

    return (
        key_condition,
        filter_expr,
        projection_expr,
        attr_names if attr_names else None,
        values if values else None,
        use_consistent,
    )


def _build_scan_params(
    model_class: type[M],
    filter_condition: Condition | None,
    consistent_read: bool | None,
    fields: list[str] | None = None,
) -> tuple[str | None, str | None, dict[str, str] | None, dict[str, Any] | None, bool]:
    """Build scan expression params.

    Returns (filter_expr, projection_expr, attr_names, attr_values, consistent).
    """
    names: dict[str, str] = {}
    values: dict[str, Any] = {}

    filter_expr = _serialize_filter(filter_condition, names, values)

    # Build projection expression
    projection_expr = None
    proj_names: dict[str, str] = {}
    if fields:
        proj_parts = []
        for i, field in enumerate(fields):
            parts = field.split(".")
            part_placeholders = []
            for part in parts:
                placeholder = f"#proj{i}_{len(part_placeholders)}"
                proj_names[placeholder] = part
                part_placeholders.append(placeholder)
            proj_parts.append(".".join(part_placeholders))
        projection_expr = ", ".join(proj_parts)

    # Merge names: filter uses {name: placeholder}, projection uses {placeholder: name}
    # Convert filter names to {placeholder: name} format and merge with projection
    attr_names = {v: k for k, v in names.items()}
    attr_names.update(proj_names)

    use_consistent = _get_consistent_read(model_class, consistent_read)

    return (
        filter_expr,
        projection_expr,
        attr_names if attr_names else None,
        values if values else None,
        use_consistent,
    )


class BaseModelResult(ABC, Generic[M]):
    """Base class for model result iterators (sync and async)."""

    _model_class: type[M]
    _result: Any
    _initialized: bool
    _as_dict: bool

    @property
    def last_evaluated_key(self) -> dict[str, Any] | None:
        """The last evaluated key for pagination."""
        if self._result is None:
            return None
        return self._result.last_evaluated_key

    def _to_instance(self, item: dict[str, Any]) -> M:
        """Convert dict to model instance and run hooks."""
        instance = self._model_class.from_dict(item)
        skip = getattr(self._model_class.model_config, "skip_hooks", False)
        if not skip:
            instance._run_hooks(HookType.AFTER_LOAD)
        return instance

    def _to_result(self, item: dict[str, Any]) -> M | dict[str, Any]:
        """Convert item based on as_dict flag."""
        if self._as_dict:
            return item
        return self._to_instance(item)

    @abstractmethod
    def _build_result(self) -> Any:
        """Build the underlying result iterator."""
        ...


class ModelQueryResult(BaseModelResult[M]):
    """Result of a Model.query() with automatic pagination."""

    def __init__(
        self,
        model_class: type[M],
        hash_key_value: Any,
        range_key_condition: Condition | None = None,
        filter_condition: Condition | None = None,
        limit: int | None = None,
        page_size: int | None = None,
        scan_index_forward: bool = True,
        consistent_read: bool | None = None,
        last_evaluated_key: dict[str, Any] | None = None,
        as_dict: bool = False,
        fields: list[str] | None = None,
    ) -> None:
        self._model_class = model_class
        self._hash_key_value = hash_key_value
        self._range_key_condition = range_key_condition
        self._filter_condition = filter_condition
        self._limit = limit
        self._page_size = page_size
        self._scan_index_forward = scan_index_forward
        self._consistent_read = consistent_read
        self._start_key = last_evaluated_key
        self._as_dict = as_dict
        self._fields = fields
        self._result: Any = None
        self._items_iter: Any = None
        self._initialized = False

    def _build_result(self) -> Any:
        client = self._model_class._get_client()
        table = self._model_class._get_table()

        key_cond, filter_expr, projection_expr, attr_names, attr_values, use_consistent = (
            _build_query_params(
                self._model_class,
                self._hash_key_value,
                self._range_key_condition,
                self._filter_condition,
                self._consistent_read,
                self._fields,
            )
        )

        return QueryResult(
            client._client,
            table,
            key_cond,
            filter_expression=filter_expr,
            projection_expression=projection_expr,
            expression_attribute_names=attr_names,
            expression_attribute_values=attr_values,
            limit=self._limit,
            page_size=self._page_size,
            scan_index_forward=self._scan_index_forward,
            last_evaluated_key=self._start_key,
            acquire_rcu=client._acquire_rcu,
            consistent_read=use_consistent,
        )

    def __iter__(self) -> ModelQueryResult[M]:
        return self

    def __next__(self) -> M | dict[str, Any]:
        if not self._initialized:
            self._result = self._build_result()
            self._items_iter = iter(self._result)
            self._initialized = True
        return self._to_result(next(self._items_iter))

    def first(self) -> M | dict[str, Any] | None:
        """Get the first result or None."""
        try:
            return next(iter(self))
        except StopIteration:
            return None


class AsyncModelQueryResult(BaseModelResult[M]):
    """Async result of a Model.query() with automatic pagination."""

    def __init__(
        self,
        model_class: type[M],
        hash_key_value: Any,
        range_key_condition: Condition | None = None,
        filter_condition: Condition | None = None,
        limit: int | None = None,
        page_size: int | None = None,
        scan_index_forward: bool = True,
        consistent_read: bool | None = None,
        last_evaluated_key: dict[str, Any] | None = None,
        as_dict: bool = False,
        fields: list[str] | None = None,
    ) -> None:
        self._model_class = model_class
        self._hash_key_value = hash_key_value
        self._range_key_condition = range_key_condition
        self._filter_condition = filter_condition
        self._limit = limit
        self._page_size = page_size
        self._scan_index_forward = scan_index_forward
        self._consistent_read = consistent_read
        self._start_key = last_evaluated_key
        self._as_dict = as_dict
        self._fields = fields
        self._result: Any = None
        self._initialized = False

    def _build_result(self) -> Any:
        client = self._model_class._get_client()
        table = self._model_class._get_table()

        key_cond, filter_expr, projection_expr, attr_names, attr_values, use_consistent = (
            _build_query_params(
                self._model_class,
                self._hash_key_value,
                self._range_key_condition,
                self._filter_condition,
                self._consistent_read,
                self._fields,
            )
        )

        return AsyncQueryResult(
            client._client,
            table,
            key_cond,
            filter_expression=filter_expr,
            projection_expression=projection_expr,
            expression_attribute_names=attr_names,
            expression_attribute_values=attr_values,
            limit=self._limit,
            page_size=self._page_size,
            scan_index_forward=self._scan_index_forward,
            last_evaluated_key=self._start_key,
            acquire_rcu=client._acquire_rcu,
            consistent_read=use_consistent,
        )

    def __aiter__(self) -> AsyncModelQueryResult[M]:
        return self

    async def __anext__(self) -> M | dict[str, Any]:
        if not self._initialized:
            self._result = self._build_result()
            self._initialized = True
        item = await self._result.__anext__()
        return self._to_result(item)

    async def first(self) -> M | dict[str, Any] | None:
        """Get the first result or None."""
        try:
            return await self.__anext__()
        except StopAsyncIteration:
            return None


class ModelScanResult(BaseModelResult[M]):
    """Result of a Model.scan() with automatic pagination."""

    def __init__(
        self,
        model_class: type[M],
        filter_condition: Condition | None = None,
        limit: int | None = None,
        page_size: int | None = None,
        consistent_read: bool | None = None,
        last_evaluated_key: dict[str, Any] | None = None,
        segment: int | None = None,
        total_segments: int | None = None,
        as_dict: bool = False,
        fields: list[str] | None = None,
    ) -> None:
        self._model_class = model_class
        self._filter_condition = filter_condition
        self._limit = limit
        self._page_size = page_size
        self._consistent_read = consistent_read
        self._start_key = last_evaluated_key
        self._segment = segment
        self._total_segments = total_segments
        self._as_dict = as_dict
        self._fields = fields
        self._result: Any = None
        self._items_iter: Any = None
        self._initialized = False

    def _build_result(self) -> Any:
        client = self._model_class._get_client()
        table = self._model_class._get_table()

        filter_expr, projection_expr, attr_names, attr_values, use_consistent = _build_scan_params(
            self._model_class, self._filter_condition, self._consistent_read, self._fields
        )

        return ScanResult(
            client._client,
            table,
            filter_expression=filter_expr,
            projection_expression=projection_expr,
            expression_attribute_names=attr_names,
            expression_attribute_values=attr_values,
            limit=self._limit,
            page_size=self._page_size,
            last_evaluated_key=self._start_key,
            acquire_rcu=client._acquire_rcu,
            consistent_read=use_consistent,
            segment=self._segment,
            total_segments=self._total_segments,
        )

    def __iter__(self) -> ModelScanResult[M]:
        return self

    def __next__(self) -> M | dict[str, Any]:
        if not self._initialized:
            self._result = self._build_result()
            self._items_iter = iter(self._result)
            self._initialized = True
        return self._to_result(next(self._items_iter))

    def first(self) -> M | dict[str, Any] | None:
        """Get the first result or None."""
        try:
            return next(iter(self))
        except StopIteration:
            return None


class AsyncModelScanResult(BaseModelResult[M]):
    """Async result of a Model.scan() with automatic pagination."""

    def __init__(
        self,
        model_class: type[M],
        filter_condition: Condition | None = None,
        limit: int | None = None,
        page_size: int | None = None,
        consistent_read: bool | None = None,
        last_evaluated_key: dict[str, Any] | None = None,
        segment: int | None = None,
        total_segments: int | None = None,
        as_dict: bool = False,
        fields: list[str] | None = None,
    ) -> None:
        self._model_class = model_class
        self._filter_condition = filter_condition
        self._limit = limit
        self._page_size = page_size
        self._consistent_read = consistent_read
        self._start_key = last_evaluated_key
        self._segment = segment
        self._total_segments = total_segments
        self._as_dict = as_dict
        self._fields = fields
        self._result: Any = None
        self._initialized = False

    def _build_result(self) -> Any:
        client = self._model_class._get_client()
        table = self._model_class._get_table()

        filter_expr, projection_expr, attr_names, attr_values, use_consistent = _build_scan_params(
            self._model_class, self._filter_condition, self._consistent_read, self._fields
        )

        return AsyncScanResult(
            client._client,
            table,
            filter_expression=filter_expr,
            projection_expression=projection_expr,
            expression_attribute_names=attr_names,
            expression_attribute_values=attr_values,
            limit=self._limit,
            page_size=self._page_size,
            last_evaluated_key=self._start_key,
            acquire_rcu=client._acquire_rcu,
            consistent_read=use_consistent,
            segment=self._segment,
            total_segments=self._total_segments,
        )

    def __aiter__(self) -> AsyncModelScanResult[M]:
        return self

    async def __anext__(self) -> M | dict[str, Any]:
        if not self._initialized:
            self._result = self._build_result()
            self._initialized = True
        item = await self._result.__anext__()
        return self._to_result(item)

    async def first(self) -> M | dict[str, Any] | None:
        """Get the first result or None."""
        try:
            return await self.__anext__()
        except StopAsyncIteration:
            return None
