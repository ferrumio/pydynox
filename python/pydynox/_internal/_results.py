"""Model query and scan result classes."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Generic, TypeVar

from pydynox.hooks import HookType
from pydynox.query import AsyncQueryResult, AsyncScanResult, QueryResult, ScanResult

if TYPE_CHECKING:
    from pydynox._internal._metrics import OperationMetrics
    from pydynox.conditions import Condition
    from pydynox.model import Model

M = TypeVar("M", bound="Model")


class BaseModelResult(ABC, Generic[M]):
    """Base class for model result iterators."""

    _model_class: type[M]
    _result: Any
    _initialized: bool

    @property
    def last_evaluated_key(self) -> dict[str, Any] | None:
        """The last evaluated key for pagination."""
        if self._result is None:
            return None
        result: dict[str, Any] | None = self._result.last_evaluated_key
        return result

    @property
    def metrics(self) -> OperationMetrics | None:
        """Metrics from the last page fetch."""
        if self._result is None:
            return None
        metrics: OperationMetrics | None = self._result.metrics
        return metrics

    def _to_instance(self, item: dict[str, Any]) -> M:
        """Convert dict to model instance and run hooks."""
        instance = self._model_class.from_dict(item)

        skip = (
            self._model_class.model_config.skip_hooks
            if hasattr(self._model_class, "model_config")
            else False
        )
        if not skip:
            instance._run_hooks(HookType.AFTER_LOAD)

        return instance

    @abstractmethod
    def _build_result(self) -> Any:
        """Build the underlying result iterator."""
        ...

    def first(self) -> M | None:
        """Get the first result or None."""
        try:
            result: M = next(iter(self))  # type: ignore[call-overload]
            return result
        except StopIteration:
            return None


class BaseAsyncModelResult(ABC, Generic[M]):
    """Base class for async model result iterators."""

    _model_class: type[M]
    _result: Any
    _initialized: bool

    @property
    def last_evaluated_key(self) -> dict[str, Any] | None:
        """The last evaluated key for pagination."""
        if self._result is None:
            return None
        result: dict[str, Any] | None = self._result.last_evaluated_key
        return result

    @property
    def metrics(self) -> OperationMetrics | None:
        """Metrics from the last page fetch."""
        if self._result is None:
            return None
        metrics: OperationMetrics | None = self._result.metrics
        return metrics

    def _to_instance(self, item: dict[str, Any]) -> M:
        """Convert dict to model instance and run hooks."""
        instance = self._model_class.from_dict(item)

        skip = (
            self._model_class.model_config.skip_hooks
            if hasattr(self._model_class, "model_config")
            else False
        )
        if not skip:
            instance._run_hooks(HookType.AFTER_LOAD)

        return instance

    @abstractmethod
    def _build_result(self) -> Any:
        """Build the underlying result iterator."""
        ...

    async def first(self) -> M | None:
        """Get the first result or None."""
        try:
            result: M = await self.__anext__()  # type: ignore[attr-defined]
            return result
        except StopAsyncIteration:
            return None


class ModelQueryResult(BaseModelResult[M]):
    """Result of a Model.query() with automatic pagination.

    Example:
        >>> for user in User.query(pk="USER#123"):
        ...     print(user.name)
    """

    def __init__(
        self,
        model_class: type[M],
        hash_key_value: Any,
        range_key_condition: Condition | None = None,
        filter_condition: Condition | None = None,
        limit: int | None = None,
        scan_index_forward: bool = True,
        consistent_read: bool | None = None,
        last_evaluated_key: dict[str, Any] | None = None,
    ) -> None:
        self._model_class = model_class
        self._hash_key_value = hash_key_value
        self._range_key_condition = range_key_condition
        self._filter_condition = filter_condition
        self._limit = limit
        self._scan_index_forward = scan_index_forward
        self._consistent_read = consistent_read
        self._start_key = last_evaluated_key
        self._result: Any = None
        self._items_iter: Any = None
        self._initialized = False

    def _build_result(self) -> Any:
        client = self._model_class._get_client()
        table = self._model_class._get_table()
        hash_key_name = self._model_class._hash_key

        if hash_key_name is None:
            raise ValueError(f"Model {self._model_class.__name__} has no hash key defined")

        names: dict[str, str] = {}
        values: dict[str, Any] = {}

        hk_placeholder = "#pk"
        hk_val_placeholder = ":pkv"
        names[hash_key_name] = hk_placeholder
        values[hk_val_placeholder] = self._hash_key_value
        key_condition = f"{hk_placeholder} = {hk_val_placeholder}"

        if self._range_key_condition is not None:
            rk_expr = self._range_key_condition.serialize(names, values)
            key_condition = f"{key_condition} AND {rk_expr}"

        filter_expr = None
        if self._filter_condition is not None:
            filter_expr = self._filter_condition.serialize(names, values)

        attr_names = {v: k for k, v in names.items()}

        use_consistent = self._consistent_read
        if use_consistent is None:
            use_consistent = getattr(self._model_class.model_config, "consistent_read", False)

        return QueryResult(
            client._client,
            table,
            key_condition,
            filter_expression=filter_expr,
            expression_attribute_names=attr_names if attr_names else None,
            expression_attribute_values=values if values else None,
            limit=self._limit,
            scan_index_forward=self._scan_index_forward,
            last_evaluated_key=self._start_key,
            acquire_rcu=client._acquire_rcu,
            consistent_read=use_consistent,
        )

    def __iter__(self) -> ModelQueryResult[M]:
        return self

    def __next__(self) -> M:
        if not self._initialized:
            self._result = self._build_result()
            self._items_iter = iter(self._result)
            self._initialized = True

        item = next(self._items_iter)
        return self._to_instance(item)


class AsyncModelQueryResult(BaseAsyncModelResult[M]):
    """Async result of a Model.query() with automatic pagination.

    Example:
        >>> async for user in User.async_query(hash_key="USER#123"):
        ...     print(user.name)
    """

    def __init__(
        self,
        model_class: type[M],
        hash_key_value: Any,
        range_key_condition: Condition | None = None,
        filter_condition: Condition | None = None,
        limit: int | None = None,
        scan_index_forward: bool = True,
        consistent_read: bool | None = None,
        last_evaluated_key: dict[str, Any] | None = None,
    ) -> None:
        self._model_class = model_class
        self._hash_key_value = hash_key_value
        self._range_key_condition = range_key_condition
        self._filter_condition = filter_condition
        self._limit = limit
        self._scan_index_forward = scan_index_forward
        self._consistent_read = consistent_read
        self._start_key = last_evaluated_key
        self._result: Any = None
        self._initialized = False

    def _build_result(self) -> Any:
        client = self._model_class._get_client()
        table = self._model_class._get_table()
        hash_key_name = self._model_class._hash_key

        if hash_key_name is None:
            raise ValueError(f"Model {self._model_class.__name__} has no hash key defined")

        names: dict[str, str] = {}
        values: dict[str, Any] = {}

        hk_placeholder = "#pk"
        hk_val_placeholder = ":pkv"
        names[hash_key_name] = hk_placeholder
        values[hk_val_placeholder] = self._hash_key_value
        key_condition = f"{hk_placeholder} = {hk_val_placeholder}"

        if self._range_key_condition is not None:
            rk_expr = self._range_key_condition.serialize(names, values)
            key_condition = f"{key_condition} AND {rk_expr}"

        filter_expr = None
        if self._filter_condition is not None:
            filter_expr = self._filter_condition.serialize(names, values)

        attr_names = {v: k for k, v in names.items()}

        use_consistent = self._consistent_read
        if use_consistent is None:
            use_consistent = getattr(self._model_class.model_config, "consistent_read", False)

        return AsyncQueryResult(
            client._client,
            table,
            key_condition,
            filter_expression=filter_expr,
            expression_attribute_names=attr_names if attr_names else None,
            expression_attribute_values=values if values else None,
            limit=self._limit,
            scan_index_forward=self._scan_index_forward,
            last_evaluated_key=self._start_key,
            acquire_rcu=client._acquire_rcu,
            consistent_read=use_consistent,
        )

    def __aiter__(self) -> AsyncModelQueryResult[M]:
        return self

    async def __anext__(self) -> M:
        if not self._initialized:
            self._result = self._build_result()
            self._initialized = True

        item = await self._result.__anext__()
        return self._to_instance(item)


class ModelScanResult(BaseModelResult[M]):
    """Result of a Model.scan() with automatic pagination.

    Example:
        >>> for user in User.scan():
        ...     print(user.name)
    """

    def __init__(
        self,
        model_class: type[M],
        filter_condition: Condition | None = None,
        limit: int | None = None,
        consistent_read: bool | None = None,
        last_evaluated_key: dict[str, Any] | None = None,
        segment: int | None = None,
        total_segments: int | None = None,
    ) -> None:
        self._model_class = model_class
        self._filter_condition = filter_condition
        self._limit = limit
        self._consistent_read = consistent_read
        self._start_key = last_evaluated_key
        self._segment = segment
        self._total_segments = total_segments
        self._result: Any = None
        self._items_iter: Any = None
        self._initialized = False

    def _build_result(self) -> Any:
        client = self._model_class._get_client()
        table = self._model_class._get_table()

        names: dict[str, str] = {}
        values: dict[str, Any] = {}

        filter_expr = None
        if self._filter_condition is not None:
            filter_expr = self._filter_condition.serialize(names, values)

        attr_names = {v: k for k, v in names.items()}

        use_consistent = self._consistent_read
        if use_consistent is None:
            use_consistent = getattr(self._model_class.model_config, "consistent_read", False)

        return ScanResult(
            client._client,
            table,
            filter_expression=filter_expr,
            expression_attribute_names=attr_names if attr_names else None,
            expression_attribute_values=values if values else None,
            limit=self._limit,
            last_evaluated_key=self._start_key,
            acquire_rcu=client._acquire_rcu,
            consistent_read=use_consistent,
            segment=self._segment,
            total_segments=self._total_segments,
        )

    def __iter__(self) -> ModelScanResult[M]:
        return self

    def __next__(self) -> M:
        if not self._initialized:
            self._result = self._build_result()
            self._items_iter = iter(self._result)
            self._initialized = True

        item = next(self._items_iter)
        return self._to_instance(item)


class AsyncModelScanResult(BaseAsyncModelResult[M]):
    """Async result of a Model.scan() with automatic pagination.

    Example:
        >>> async for user in User.async_scan():
        ...     print(user.name)
    """

    def __init__(
        self,
        model_class: type[M],
        filter_condition: Condition | None = None,
        limit: int | None = None,
        consistent_read: bool | None = None,
        last_evaluated_key: dict[str, Any] | None = None,
        segment: int | None = None,
        total_segments: int | None = None,
    ) -> None:
        self._model_class = model_class
        self._filter_condition = filter_condition
        self._limit = limit
        self._consistent_read = consistent_read
        self._start_key = last_evaluated_key
        self._segment = segment
        self._total_segments = total_segments
        self._result: Any = None
        self._initialized = False

    def _build_result(self) -> Any:
        client = self._model_class._get_client()
        table = self._model_class._get_table()

        names: dict[str, str] = {}
        values: dict[str, Any] = {}

        filter_expr = None
        if self._filter_condition is not None:
            filter_expr = self._filter_condition.serialize(names, values)

        attr_names = {v: k for k, v in names.items()}

        use_consistent = self._consistent_read
        if use_consistent is None:
            use_consistent = getattr(self._model_class.model_config, "consistent_read", False)

        return AsyncScanResult(
            client._client,
            table,
            filter_expression=filter_expr,
            expression_attribute_names=attr_names if attr_names else None,
            expression_attribute_values=values if values else None,
            limit=self._limit,
            last_evaluated_key=self._start_key,
            acquire_rcu=client._acquire_rcu,
            consistent_read=use_consistent,
            segment=self._segment,
            total_segments=self._total_segments,
        )

    def __aiter__(self) -> AsyncModelScanResult[M]:
        return self

    async def __anext__(self) -> M:
        if not self._initialized:
            self._result = self._build_result()
            self._initialized = True

        item = await self._result.__anext__()
        return self._to_instance(item)
