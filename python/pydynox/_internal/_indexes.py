"""Internal implementation of secondary indexes.

This module contains the implementation of GlobalSecondaryIndex and LocalSecondaryIndex.
Public API is exported from pydynox.indexes.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Generic, Protocol, TypeVar

if TYPE_CHECKING:
    from pydynox.conditions import Condition
    from pydynox.model import Model

M = TypeVar("M", bound="Model")


class _TemplateAttr(Protocol):
    """Protocol for attributes with template support."""

    has_template: bool
    placeholders: list[str]

    def build_key(self, values: dict[str, Any]) -> str: ...


class GlobalSecondaryIndex(Generic[M]):
    """Global Secondary Index definition for a Model.

    GSIs let you query by attributes other than the table's primary key.
    Define them as class attributes on your Model.

    Supports multi-attribute composite keys (up to 4 attributes per key).

    Args:
        index_name: Name of the GSI in DynamoDB.
        hash_key: Attribute name(s) for the GSI partition key.
            Can be a single string or list of up to 4 strings.
        range_key: Optional attribute name(s) for the GSI sort key.
            Can be a single string or list of up to 4 strings.
        projection: Attributes to project. Options:
            - "ALL" (default): All attributes
            - "KEYS_ONLY": Only key attributes
            - list of attribute names: Specific attributes

    Example:
        >>> class User(Model):
        ...     model_config = ModelConfig(table="users")
        ...     pk = StringAttribute(hash_key=True)
        ...     email = StringAttribute()
        ...
        ...     email_index = GlobalSecondaryIndex(
        ...         index_name="email-index",
        ...         hash_key="email",
        ...     )
        >>>
        >>> users = User.email_index.query(email="john@example.com")
    """

    def __init__(
        self,
        index_name: str,
        hash_key: str | list[str],
        range_key: str | list[str] | None = None,
        projection: str | list[str] = "ALL",
    ) -> None:
        self.index_name = index_name

        # Normalize to list
        self.hash_keys = [hash_key] if isinstance(hash_key, str) else list(hash_key)
        self.range_keys = (
            []
            if range_key is None
            else [range_key]
            if isinstance(range_key, str)
            else list(range_key)
        )

        # Validate max 4 attributes per key
        if len(self.hash_keys) > 4:
            raise ValueError(
                f"GSI '{index_name}': hash_key can have at most 4 attributes, "
                f"got {len(self.hash_keys)}"
            )
        if len(self.range_keys) > 4:
            raise ValueError(
                f"GSI '{index_name}': range_key can have at most 4 attributes, "
                f"got {len(self.range_keys)}"
            )
        if not self.hash_keys:
            raise ValueError(f"GSI '{index_name}': hash_key is required")

        self.projection = projection

        # For backward compatibility
        self.hash_key = self.hash_keys[0]
        self.range_key = self.range_keys[0] if self.range_keys else None

        # Set by Model metaclass
        self._model_class: type[M] | None = None
        self._attr_name: str | None = None

    def __set_name__(self, owner: type[M], name: str) -> None:
        self._attr_name = name

    def _bind_to_model(self, model_class: type[M]) -> None:
        self._model_class = model_class

    def _get_model_class(self) -> type[M]:
        if self._model_class is None:
            raise RuntimeError(
                f"GSI '{self.index_name}' is not bound to a model. "
                "Make sure it's defined as a class attribute on a Model subclass."
            )
        return self._model_class

    def _resolve_hash_key_values(
        self, model_class: type[M], key_values: dict[str, Any]
    ) -> dict[str, Any]:
        """Resolve hash key values, building from templates if needed.

        For inverted indexes where hash_key="sk", this detects that the user
        passed template placeholders (e.g., order_id="456") and builds the
        actual key value using the template (e.g., "ORDER#456").
        """
        resolved: dict[str, Any] = {}
        attributes = model_class._attributes

        for attr_name in self.hash_keys:
            # Direct value provided
            if attr_name in key_values:
                resolved[attr_name] = key_values[attr_name]
                continue

            # Check if attribute has template
            attr = attributes.get(attr_name)
            if attr is None:
                raise ValueError(f"Attribute '{attr_name}' not found on {model_class.__name__}")

            if hasattr(attr, "has_template") and attr.has_template:
                # Cast to template protocol for type checker
                tattr: _TemplateAttr = attr  # type: ignore[assignment]
                # Try to build from template placeholders
                placeholders = tattr.placeholders
                missing = [p for p in placeholders if p not in key_values]
                if not missing:
                    # All placeholders provided, build the key
                    values = {p: key_values[p] for p in placeholders}
                    resolved[attr_name] = tattr.build_key(values)
                    continue

            # Neither direct value nor template placeholders provided
            raise ValueError(
                f"GSI query requires '{attr_name}' or its template placeholders. "
                f"Got: {list(key_values.keys())}"
            )

        return resolved

    def sync_query(
        self,
        range_key_condition: Condition | None = None,
        filter_condition: Condition | None = None,
        limit: int | None = None,
        page_size: int | None = None,
        scan_index_forward: bool = True,
        last_evaluated_key: dict[str, Any] | None = None,
        **key_values: Any,
    ) -> GSIQueryResult[M]:
        """Sync query the GSI.

        For inverted indexes with templates, you can pass template placeholders:
            # If sk has template="ORDER#{order_id}" and GSI has hash_key="sk"
            inverted_index.sync_query(order_id="456")
            # Internally builds: sk="ORDER#456"
        """
        model_class = self._get_model_class()
        resolved_values = self._resolve_hash_key_values(model_class, key_values)

        return GSIQueryResult(
            model_class=model_class,
            index_name=self.index_name,
            hash_keys=self.hash_keys,
            hash_key_values=resolved_values,
            range_keys=self.range_keys,
            range_key_condition=range_key_condition,
            filter_condition=filter_condition,
            limit=limit,
            page_size=page_size,
            scan_index_forward=scan_index_forward,
            last_evaluated_key=last_evaluated_key,
        )

    def query(
        self,
        range_key_condition: Condition | None = None,
        filter_condition: Condition | None = None,
        limit: int | None = None,
        page_size: int | None = None,
        scan_index_forward: bool = True,
        last_evaluated_key: dict[str, Any] | None = None,
        **key_values: Any,
    ) -> AsyncGSIQueryResult[M]:
        """Query the GSI (async).

        For inverted indexes with templates, you can pass template placeholders:
            # If sk has template="ORDER#{order_id}" and GSI has hash_key="sk"
            async for item in inverted_index.query(order_id="456"):
                print(item)
            # Internally builds: sk="ORDER#456"
        """
        model_class = self._get_model_class()
        resolved_values = self._resolve_hash_key_values(model_class, key_values)

        return AsyncGSIQueryResult(
            model_class=model_class,
            index_name=self.index_name,
            hash_keys=self.hash_keys,
            hash_key_values=resolved_values,
            range_keys=self.range_keys,
            range_key_condition=range_key_condition,
            filter_condition=filter_condition,
            limit=limit,
            page_size=page_size,
            scan_index_forward=scan_index_forward,
            last_evaluated_key=last_evaluated_key,
        )

    def to_dynamodb_definition(self) -> dict[str, Any]:
        """Convert to DynamoDB GSI definition format."""
        key_schema: list[dict[str, str]] = []

        for attr_name in self.hash_keys:
            key_schema.append({"AttributeName": attr_name, "KeyType": "HASH"})

        for attr_name in self.range_keys:
            key_schema.append({"AttributeName": attr_name, "KeyType": "RANGE"})

        projection: dict[str, Any]
        match self.projection:
            case "ALL":
                projection = {"ProjectionType": "ALL"}
            case "KEYS_ONLY":
                projection = {"ProjectionType": "KEYS_ONLY"}
            case list() as attrs:
                projection = {
                    "ProjectionType": "INCLUDE",
                    "NonKeyAttributes": attrs,
                }
            case _:
                projection = {"ProjectionType": "ALL"}

        return {
            "IndexName": self.index_name,
            "KeySchema": key_schema,
            "Projection": projection,
        }

    def to_create_table_definition(self, model_class: type[M]) -> dict[str, Any]:
        """Convert to format expected by client.create_table()."""
        attributes = model_class._attributes

        hash_keys: list[tuple[str, str]] = []
        for attr_name in self.hash_keys:
            if attr_name not in attributes:
                raise ValueError(
                    f"GSI '{self.index_name}' references attribute '{attr_name}' "
                    f"which is not defined on {model_class.__name__}"
                )
            attr_type = attributes[attr_name].attr_type
            hash_keys.append((attr_name, attr_type))

        range_keys: list[tuple[str, str]] = []
        for attr_name in self.range_keys:
            if attr_name not in attributes:
                raise ValueError(
                    f"GSI '{self.index_name}' references attribute '{attr_name}' "
                    f"which is not defined on {model_class.__name__}"
                )
            attr_type = attributes[attr_name].attr_type
            range_keys.append((attr_name, attr_type))

        projection_type: str
        non_key_attributes: list[str] | None = None
        match self.projection:
            case "ALL":
                projection_type = "ALL"
            case "KEYS_ONLY":
                projection_type = "KEYS_ONLY"
            case list() as attrs:
                projection_type = "INCLUDE"
                non_key_attributes = attrs
            case _:
                projection_type = "ALL"

        result: dict[str, Any] = {
            "index_name": self.index_name,
            "projection": projection_type,
        }

        if len(hash_keys) == 1:
            result["hash_key"] = hash_keys[0]
        else:
            result["hash_keys"] = hash_keys

        if range_keys:
            if len(range_keys) == 1:
                result["range_key"] = range_keys[0]
            else:
                result["range_keys"] = range_keys

        if non_key_attributes:
            result["non_key_attributes"] = non_key_attributes

        return result


class GSIQueryResult(Generic[M]):
    """Result of a GSI query with automatic pagination."""

    def __init__(
        self,
        model_class: type[M],
        index_name: str,
        hash_keys: list[str],
        hash_key_values: dict[str, Any],
        range_keys: list[str] | None = None,
        range_key_condition: Condition | None = None,
        filter_condition: Condition | None = None,
        limit: int | None = None,
        page_size: int | None = None,
        scan_index_forward: bool = True,
        last_evaluated_key: dict[str, Any] | None = None,
    ) -> None:
        self._model_class = model_class
        self._index_name = index_name
        self._hash_keys = hash_keys
        self._hash_key_values = hash_key_values
        self._range_keys = range_keys or []
        self._range_key_condition = range_key_condition
        self._filter_condition = filter_condition
        self._limit = limit
        self._page_size = page_size
        self._scan_index_forward = scan_index_forward
        self._start_key = last_evaluated_key

        self._query_result: Any = None
        self._items_iter: Any = None
        self._initialized = False

    @property
    def last_evaluated_key(self) -> dict[str, Any] | None:
        if self._query_result is None:
            return None
        result: dict[str, Any] | None = self._query_result.last_evaluated_key
        return result

    def _build_query(self) -> Any:
        from pydynox.query import QueryResult

        client = self._model_class._get_client()
        table = self._model_class._get_table()

        names: dict[str, str] = {}
        values: dict[str, Any] = {}

        key_conditions: list[str] = []
        for i, attr_name in enumerate(self._hash_keys):
            name_placeholder = f"#gsi_hk{i}"
            value_placeholder = f":gsi_hkv{i}"
            names[attr_name] = name_placeholder
            values[value_placeholder] = self._hash_key_values[attr_name]
            key_conditions.append(f"{name_placeholder} = {value_placeholder}")

        key_condition = " AND ".join(key_conditions)

        if self._range_key_condition is not None:
            rk_expr = self._range_key_condition.serialize(names, values)
            key_condition = f"{key_condition} AND {rk_expr}"

        filter_expr = None
        if self._filter_condition is not None:
            filter_expr = self._filter_condition.serialize(names, values)

        attr_names = {placeholder: attr_name for attr_name, placeholder in names.items()}

        return QueryResult(
            client._client,
            table,
            key_condition,
            filter_expression=filter_expr,
            expression_attribute_names=attr_names if attr_names else None,
            expression_attribute_values=values if values else None,
            limit=self._limit,
            page_size=self._page_size,
            scan_index_forward=self._scan_index_forward,
            index_name=self._index_name,
            last_evaluated_key=self._start_key,
            acquire_rcu=client._acquire_rcu,
        )

    def __iter__(self) -> GSIQueryResult[M]:
        return self

    def __next__(self) -> M:
        if not self._initialized:
            self._query_result = self._build_query()
            self._items_iter = iter(self._query_result)
            self._initialized = True

        item = next(self._items_iter)
        instance = self._model_class.from_dict(item)

        skip = (
            self._model_class.model_config.skip_hooks
            if hasattr(self._model_class, "model_config")
            else False
        )
        if not skip:
            from pydynox.hooks import HookType

            instance._run_hooks(HookType.AFTER_LOAD)

        return instance


class AsyncGSIQueryResult(Generic[M]):
    """Async result of a GSI query with automatic pagination."""

    def __init__(
        self,
        model_class: type[M],
        index_name: str,
        hash_keys: list[str],
        hash_key_values: dict[str, Any],
        range_keys: list[str] | None = None,
        range_key_condition: Condition | None = None,
        filter_condition: Condition | None = None,
        limit: int | None = None,
        page_size: int | None = None,
        scan_index_forward: bool = True,
        last_evaluated_key: dict[str, Any] | None = None,
    ) -> None:
        self._model_class = model_class
        self._index_name = index_name
        self._hash_keys = hash_keys
        self._hash_key_values = hash_key_values
        self._range_keys = range_keys or []
        self._range_key_condition = range_key_condition
        self._filter_condition = filter_condition
        self._limit = limit
        self._page_size = page_size
        self._scan_index_forward = scan_index_forward
        self._start_key = last_evaluated_key

        self._query_result: Any = None
        self._initialized = False

    @property
    def last_evaluated_key(self) -> dict[str, Any] | None:
        """Get the last evaluated key for pagination."""
        if self._query_result is None:
            return None
        result: dict[str, Any] | None = self._query_result.last_evaluated_key
        return result

    def _build_query(self) -> Any:
        from pydynox.query import AsyncQueryResult

        client = self._model_class._get_client()
        table = self._model_class._get_table()

        names: dict[str, str] = {}
        values: dict[str, Any] = {}

        key_conditions: list[str] = []
        for i, attr_name in enumerate(self._hash_keys):
            name_placeholder = f"#gsi_hk{i}"
            value_placeholder = f":gsi_hkv{i}"
            names[attr_name] = name_placeholder
            values[value_placeholder] = self._hash_key_values[attr_name]
            key_conditions.append(f"{name_placeholder} = {value_placeholder}")

        key_condition = " AND ".join(key_conditions)

        if self._range_key_condition is not None:
            rk_expr = self._range_key_condition.serialize(names, values)
            key_condition = f"{key_condition} AND {rk_expr}"

        filter_expr = None
        if self._filter_condition is not None:
            filter_expr = self._filter_condition.serialize(names, values)

        attr_names = {placeholder: attr_name for attr_name, placeholder in names.items()}

        return AsyncQueryResult(
            client._client,
            table,
            key_condition,
            filter_expression=filter_expr,
            expression_attribute_names=attr_names if attr_names else None,
            expression_attribute_values=values if values else None,
            limit=self._limit,
            page_size=self._page_size,
            scan_index_forward=self._scan_index_forward,
            index_name=self._index_name,
            last_evaluated_key=self._start_key,
            acquire_rcu=client._acquire_rcu,
        )

    def __aiter__(self) -> AsyncGSIQueryResult[M]:
        return self

    async def __anext__(self) -> M:
        if not self._initialized:
            self._query_result = self._build_query()
            self._initialized = True

        item = await self._query_result.__anext__()
        instance = self._model_class.from_dict(item)

        skip = (
            self._model_class.model_config.skip_hooks
            if hasattr(self._model_class, "model_config")
            else False
        )
        if not skip:
            from pydynox.hooks import HookType

            instance._run_hooks(HookType.AFTER_LOAD)

        return instance

    async def first(self) -> M | None:
        """Get the first item or None."""
        try:
            return await self.__anext__()
        except StopAsyncIteration:
            return None


class LocalSecondaryIndex(Generic[M]):
    """Local Secondary Index definition for a Model.

    LSIs let you query by the same hash key but a different sort key.
    They must be created with the table (cannot be added later).

    Unlike GSIs, LSIs:
    - Share the table's hash key (you don't specify one)
    - Only have a range key (the alternate sort key)
    - Support strongly consistent reads
    - Share provisioned throughput with the table

    Args:
        index_name: Name of the LSI in DynamoDB.
        range_key: Attribute name for the LSI sort key.
        projection: Attributes to project. Options:
            - "ALL" (default): All attributes
            - "KEYS_ONLY": Only key attributes
            - list of attribute names: Specific attributes

    Example:
        >>> class User(Model):
        ...     model_config = ModelConfig(table="users")
        ...     pk = StringAttribute(hash_key=True)
        ...     sk = StringAttribute(range_key=True)
        ...     status = StringAttribute()
        ...
        ...     status_index = LocalSecondaryIndex(
        ...         index_name="status-index",
        ...         range_key="status",
        ...     )
        >>>
        >>> for user in User.status_index.query(pk="USER#1"):
        ...     print(user.status)
    """

    def __init__(
        self,
        index_name: str,
        range_key: str,
        projection: str | list[str] = "ALL",
    ) -> None:
        self.index_name = index_name
        self.range_key = range_key
        self.projection = projection

        self._model_class: type[M] | None = None
        self._attr_name: str | None = None

    def __set_name__(self, owner: type[M], name: str) -> None:
        self._attr_name = name

    def _bind_to_model(self, model_class: type[M]) -> None:
        self._model_class = model_class

    def _get_model_class(self) -> type[M]:
        if self._model_class is None:
            raise RuntimeError(
                f"LSI '{self.index_name}' is not bound to a model. "
                "Make sure it's defined as a class attribute on a Model subclass."
            )
        return self._model_class

    def sync_query(
        self,
        range_key_condition: Condition | None = None,
        filter_condition: Condition | None = None,
        limit: int | None = None,
        page_size: int | None = None,
        scan_index_forward: bool = True,
        consistent_read: bool = False,
        last_evaluated_key: dict[str, Any] | None = None,
        **key_values: Any,
    ) -> LSIQueryResult[M]:
        """Sync query the LSI."""
        model_class = self._get_model_class()

        hash_key_name = model_class._hash_key
        if hash_key_name is None:
            raise ValueError(f"Model {model_class.__name__} has no hash_key defined")

        if hash_key_name not in key_values:
            raise ValueError(
                f"LSI sync_query requires the table's hash key '{hash_key_name}'. "
                f"Got: {list(key_values.keys())}"
            )

        return LSIQueryResult(
            model_class=model_class,
            index_name=self.index_name,
            hash_key_name=hash_key_name,
            hash_key_value=key_values[hash_key_name],
            range_key_name=self.range_key,
            range_key_condition=range_key_condition,
            filter_condition=filter_condition,
            limit=limit,
            page_size=page_size,
            scan_index_forward=scan_index_forward,
            consistent_read=consistent_read,
            last_evaluated_key=last_evaluated_key,
        )

    def query(
        self,
        range_key_condition: Condition | None = None,
        filter_condition: Condition | None = None,
        limit: int | None = None,
        page_size: int | None = None,
        scan_index_forward: bool = True,
        consistent_read: bool = False,
        last_evaluated_key: dict[str, Any] | None = None,
        **key_values: Any,
    ) -> AsyncLSIQueryResult[M]:
        """Query the LSI (async)."""
        model_class = self._get_model_class()

        hash_key_name = model_class._hash_key
        if hash_key_name is None:
            raise ValueError(f"Model {model_class.__name__} has no hash_key defined")

        if hash_key_name not in key_values:
            raise ValueError(
                f"LSI query requires the table's hash key '{hash_key_name}'. "
                f"Got: {list(key_values.keys())}"
            )

        return AsyncLSIQueryResult(
            model_class=model_class,
            index_name=self.index_name,
            hash_key_name=hash_key_name,
            hash_key_value=key_values[hash_key_name],
            range_key_name=self.range_key,
            range_key_condition=range_key_condition,
            filter_condition=filter_condition,
            limit=limit,
            page_size=page_size,
            scan_index_forward=scan_index_forward,
            consistent_read=consistent_read,
            last_evaluated_key=last_evaluated_key,
        )

    def to_create_table_definition(self, model_class: type[M]) -> dict[str, Any]:
        """Convert to format expected by client.create_table()."""
        attributes = model_class._attributes

        if self.range_key not in attributes:
            raise ValueError(
                f"LSI '{self.index_name}' references attribute '{self.range_key}' "
                f"which is not defined on {model_class.__name__}"
            )

        attr_type = attributes[self.range_key].attr_type

        projection_type: str
        non_key_attributes: list[str] | None = None
        match self.projection:
            case "ALL":
                projection_type = "ALL"
            case "KEYS_ONLY":
                projection_type = "KEYS_ONLY"
            case list() as attrs:
                projection_type = "INCLUDE"
                non_key_attributes = attrs
            case _:
                projection_type = "ALL"

        result: dict[str, Any] = {
            "index_name": self.index_name,
            "range_key": (self.range_key, attr_type),
            "projection": projection_type,
        }

        if non_key_attributes:
            result["non_key_attributes"] = non_key_attributes

        return result


class LSIQueryResult(Generic[M]):
    """Result of an LSI query with automatic pagination."""

    def __init__(
        self,
        model_class: type[M],
        index_name: str,
        hash_key_name: str,
        hash_key_value: Any,
        range_key_name: str,
        range_key_condition: Condition | None = None,
        filter_condition: Condition | None = None,
        limit: int | None = None,
        page_size: int | None = None,
        scan_index_forward: bool = True,
        last_evaluated_key: dict[str, Any] | None = None,
        consistent_read: bool = False,
    ) -> None:
        self._model_class = model_class
        self._index_name = index_name
        self._hash_key_name = hash_key_name
        self._hash_key_value = hash_key_value
        self._range_key_name = range_key_name
        self._range_key_condition = range_key_condition
        self._filter_condition = filter_condition
        self._limit = limit
        self._page_size = page_size
        self._scan_index_forward = scan_index_forward
        self._start_key = last_evaluated_key
        self._consistent_read = consistent_read

        self._query_result: Any = None
        self._items_iter: Any = None
        self._initialized = False

    @property
    def last_evaluated_key(self) -> dict[str, Any] | None:
        if self._query_result is None:
            return None
        result: dict[str, Any] | None = self._query_result.last_evaluated_key
        return result

    def _build_query(self) -> Any:
        from pydynox.query import QueryResult

        client = self._model_class._get_client()
        table = self._model_class._get_table()

        names: dict[str, str] = {}
        values: dict[str, Any] = {}

        name_placeholder = "#lsi_hk"
        value_placeholder = ":lsi_hkv"
        names[self._hash_key_name] = name_placeholder
        values[value_placeholder] = self._hash_key_value
        key_condition = f"{name_placeholder} = {value_placeholder}"

        if self._range_key_condition is not None:
            rk_expr = self._range_key_condition.serialize(names, values)
            key_condition = f"{key_condition} AND {rk_expr}"

        filter_expr = None
        if self._filter_condition is not None:
            filter_expr = self._filter_condition.serialize(names, values)

        attr_names = {placeholder: attr_name for attr_name, placeholder in names.items()}

        return QueryResult(
            client._client,
            table,
            key_condition,
            filter_expression=filter_expr,
            expression_attribute_names=attr_names if attr_names else None,
            expression_attribute_values=values if values else None,
            limit=self._limit,
            page_size=self._page_size,
            scan_index_forward=self._scan_index_forward,
            index_name=self._index_name,
            last_evaluated_key=self._start_key,
            acquire_rcu=client._acquire_rcu,
            consistent_read=self._consistent_read,
        )

    def __iter__(self) -> LSIQueryResult[M]:
        return self

    def __next__(self) -> M:
        if not self._initialized:
            self._query_result = self._build_query()
            self._items_iter = iter(self._query_result)
            self._initialized = True

        item = next(self._items_iter)
        instance = self._model_class.from_dict(item)

        skip = (
            self._model_class.model_config.skip_hooks
            if hasattr(self._model_class, "model_config")
            else False
        )
        if not skip:
            from pydynox.hooks import HookType

            instance._run_hooks(HookType.AFTER_LOAD)

        return instance


class AsyncLSIQueryResult(Generic[M]):
    """Async result of an LSI query with automatic pagination."""

    def __init__(
        self,
        model_class: type[M],
        index_name: str,
        hash_key_name: str,
        hash_key_value: Any,
        range_key_name: str,
        range_key_condition: Condition | None = None,
        filter_condition: Condition | None = None,
        limit: int | None = None,
        page_size: int | None = None,
        scan_index_forward: bool = True,
        last_evaluated_key: dict[str, Any] | None = None,
        consistent_read: bool = False,
    ) -> None:
        self._model_class = model_class
        self._index_name = index_name
        self._hash_key_name = hash_key_name
        self._hash_key_value = hash_key_value
        self._range_key_name = range_key_name
        self._range_key_condition = range_key_condition
        self._filter_condition = filter_condition
        self._limit = limit
        self._page_size = page_size
        self._scan_index_forward = scan_index_forward
        self._start_key = last_evaluated_key
        self._consistent_read = consistent_read

        self._query_result: Any = None
        self._initialized = False

    @property
    def last_evaluated_key(self) -> dict[str, Any] | None:
        """Get the last evaluated key for pagination."""
        if self._query_result is None:
            return None
        result: dict[str, Any] | None = self._query_result.last_evaluated_key
        return result

    def _build_query(self) -> Any:
        from pydynox.query import AsyncQueryResult

        client = self._model_class._get_client()
        table = self._model_class._get_table()

        names: dict[str, str] = {}
        values: dict[str, Any] = {}

        name_placeholder = "#lsi_hk"
        value_placeholder = ":lsi_hkv"
        names[self._hash_key_name] = name_placeholder
        values[value_placeholder] = self._hash_key_value
        key_condition = f"{name_placeholder} = {value_placeholder}"

        if self._range_key_condition is not None:
            rk_expr = self._range_key_condition.serialize(names, values)
            key_condition = f"{key_condition} AND {rk_expr}"

        filter_expr = None
        if self._filter_condition is not None:
            filter_expr = self._filter_condition.serialize(names, values)

        attr_names = {placeholder: attr_name for attr_name, placeholder in names.items()}

        return AsyncQueryResult(
            client._client,
            table,
            key_condition,
            filter_expression=filter_expr,
            expression_attribute_names=attr_names if attr_names else None,
            expression_attribute_values=values if values else None,
            limit=self._limit,
            page_size=self._page_size,
            scan_index_forward=self._scan_index_forward,
            index_name=self._index_name,
            last_evaluated_key=self._start_key,
            acquire_rcu=client._acquire_rcu,
            consistent_read=self._consistent_read,
        )

    def __aiter__(self) -> AsyncLSIQueryResult[M]:
        return self

    async def __anext__(self) -> M:
        if not self._initialized:
            self._query_result = self._build_query()
            self._initialized = True

        item = await self._query_result.__anext__()
        instance = self._model_class.from_dict(item)

        skip = (
            self._model_class.model_config.skip_hooks
            if hasattr(self._model_class, "model_config")
            else False
        )
        if not skip:
            from pydynox.hooks import HookType

            instance._run_hooks(HookType.AFTER_LOAD)

        return instance

    async def first(self) -> M | None:
        """Get the first item or None."""
        try:
            return await self.__anext__()
        except StopAsyncIteration:
            return None
