"""Global Secondary Index support for pydynox models.

GSIs allow querying by non-key attributes. Define them on your model
and query using the index's partition key.

Supports multi-attribute composite keys (up to 4 attributes per key).
See: https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/GSI.DesignPattern.MultiAttributeKeys.html

Example:
    >>> from pydynox import Model, ModelConfig
    >>> from pydynox.attributes import StringAttribute
    >>> from pydynox.indexes import GlobalSecondaryIndex
    >>>
    >>> class User(Model):
    ...     model_config = ModelConfig(table="users")
    ...     pk = StringAttribute(hash_key=True)
    ...     sk = StringAttribute(range_key=True)
    ...     email = StringAttribute()
    ...     status = StringAttribute()
    ...
    ...     # Single-attribute GSI (classic)
    ...     email_index = GlobalSecondaryIndex(
    ...         index_name="email-index",
    ...         hash_key="email",
    ...     )
    ...
    ...     # Multi-attribute GSI (new in Nov 2025)
    ...     location_index = GlobalSecondaryIndex(
    ...         index_name="location-index",
    ...         hash_key=["tenant_id", "region"],
    ...         range_key=["created_at", "id"],
    ...     )
    >>>
    >>> # Query single-attribute GSI
    >>> for user in User.email_index.query(email="john@example.com"):
    ...     print(user.pk)
    >>>
    >>> # Query multi-attribute GSI (all hash key attrs required)
    >>> for user in User.location_index.query(
    ...     tenant_id="ACME",
    ...     region="us-east-1",
    ... ):
    ...     print(user.email)
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Generic, TypeVar

if TYPE_CHECKING:
    from pydynox.conditions import Condition
    from pydynox.model import Model

M = TypeVar("M", bound="Model")

__all__ = ["GlobalSecondaryIndex"]


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
        ...     tenant_id = StringAttribute()
        ...     region = StringAttribute()
        ...
        ...     # Single-attribute key
        ...     email_index = GlobalSecondaryIndex(
        ...         index_name="email-index",
        ...         hash_key="email",
        ...     )
        ...
        ...     # Multi-attribute key
        ...     location_index = GlobalSecondaryIndex(
        ...         index_name="location-index",
        ...         hash_key=["tenant_id", "region"],
        ...     )
        >>>
        >>> # Query single-attribute
        >>> users = User.email_index.query(email="john@example.com")
        >>>
        >>> # Query multi-attribute (all hash key attrs required)
        >>> users = User.location_index.query(tenant_id="ACME", region="us-east-1")
    """

    def __init__(
        self,
        index_name: str,
        hash_key: str | list[str],
        range_key: str | list[str] | None = None,
        projection: str | list[str] = "ALL",
    ) -> None:
        """Create a GSI definition.

        Args:
            index_name: Name of the GSI in DynamoDB.
            hash_key: Attribute name(s) for the GSI partition key.
                Single string or list of up to 4 strings.
            range_key: Optional attribute name(s) for the GSI sort key.
                Single string or list of up to 4 strings.
            projection: Projection type or list of attributes.

        Raises:
            ValueError: If hash_key or range_key has more than 4 attributes.
        """
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
        """Called when the descriptor is assigned to a class attribute."""
        self._attr_name = name

    def _bind_to_model(self, model_class: type[M]) -> None:
        """Bind this index to a model class."""
        self._model_class = model_class

    def _get_model_class(self) -> type[M]:
        """Get the bound model class or raise error."""
        if self._model_class is None:
            raise RuntimeError(
                f"GSI '{self.index_name}' is not bound to a model. "
                "Make sure it's defined as a class attribute on a Model subclass."
            )
        return self._model_class

    def query(
        self,
        range_key_condition: Condition | None = None,
        filter_condition: Condition | None = None,
        limit: int | None = None,
        scan_index_forward: bool = True,
        **key_values: Any,
    ) -> GSIQueryResult[M]:
        """Query the GSI.

        For multi-attribute keys:
        - All hash key attributes are required
        - Sort key attributes are optional (left-to-right prefix)

        Args:
            range_key_condition: Optional condition on the GSI range key.
                Use attribute comparison methods like `begins_with`, `between`, etc.
            filter_condition: Optional filter on non-key attributes.
                Applied after the query, still consumes RCU for filtered items.
            limit: Max items per page (not total).
            scan_index_forward: Sort order. True = ascending (default), False = descending.
            **key_values: The GSI key values. Must include all hash_key attributes.

        Returns:
            GSIQueryResult that can be iterated.

        Example:
            >>> # Single-attribute GSI
            >>> for user in User.email_index.query(email="john@example.com"):
            ...     print(user.name)
            >>>
            >>> # Multi-attribute GSI (all hash key attrs required)
            >>> for user in User.location_index.query(
            ...     tenant_id="ACME",
            ...     region="us-east-1",
            ... ):
            ...     print(user.email)
            >>>
            >>> # With range key condition
            >>> for user in User.status_index.query(
            ...     status="active",
            ...     range_key_condition=User.created_at > "2024-01-01",
            ... ):
            ...     print(user.email)
        """
        model_class = self._get_model_class()

        # Validate all hash key attributes are provided
        missing_hash_keys = [k for k in self.hash_keys if k not in key_values]
        if missing_hash_keys:
            raise ValueError(
                f"GSI query requires all hash key attributes: {self.hash_keys}. "
                f"Missing: {missing_hash_keys}"
            )

        return GSIQueryResult(
            model_class=model_class,
            index_name=self.index_name,
            hash_keys=self.hash_keys,
            hash_key_values={k: key_values[k] for k in self.hash_keys},
            range_keys=self.range_keys,
            range_key_condition=range_key_condition,
            filter_condition=filter_condition,
            limit=limit,
            scan_index_forward=scan_index_forward,
        )

    def to_dynamodb_definition(self) -> dict[str, Any]:
        """Convert to DynamoDB GSI definition format.

        Used when creating tables with GSIs.
        Supports multi-attribute composite keys.

        Returns:
            Dict in DynamoDB CreateTable GSI format.
        """
        # Build key schema with multiple HASH/RANGE entries for multi-attribute keys
        key_schema: list[dict[str, str]] = []

        # Add all hash key attributes (all with KeyType: HASH)
        for attr_name in self.hash_keys:
            key_schema.append({"AttributeName": attr_name, "KeyType": "HASH"})

        # Add all range key attributes (all with KeyType: RANGE)
        for attr_name in self.range_keys:
            key_schema.append({"AttributeName": attr_name, "KeyType": "RANGE"})

        # Build projection
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
        """Convert to format expected by client.create_table().

        This includes attribute types from the model's attributes.

        Args:
            model_class: The model class to get attribute types from.

        Returns:
            Dict with index_name, hash_keys/hash_key, range_keys/range_key, projection.
        """
        # Get attribute types from model
        attributes = model_class._attributes

        # Build hash_keys with types
        hash_keys: list[tuple[str, str]] = []
        for attr_name in self.hash_keys:
            if attr_name not in attributes:
                raise ValueError(
                    f"GSI '{self.index_name}' references attribute '{attr_name}' "
                    f"which is not defined on {model_class.__name__}"
                )
            attr_type = attributes[attr_name].attr_type
            hash_keys.append((attr_name, attr_type))

        # Build range_keys with types
        range_keys: list[tuple[str, str]] = []
        for attr_name in self.range_keys:
            if attr_name not in attributes:
                raise ValueError(
                    f"GSI '{self.index_name}' references attribute '{attr_name}' "
                    f"which is not defined on {model_class.__name__}"
                )
            attr_type = attributes[attr_name].attr_type
            range_keys.append((attr_name, attr_type))

        # Build projection string
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

        # Use multi-attribute format if more than one key attribute
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
    """Result of a GSI query with automatic pagination.

    Iterate over results to get model instances.
    Access `last_evaluated_key` for manual pagination.

    Example:
        >>> results = User.email_index.query(email="john@example.com")
        >>> for user in results:
        ...     print(user.name)
    """

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
        self._scan_index_forward = scan_index_forward
        self._start_key = last_evaluated_key

        # Iteration state
        self._query_result: Any = None
        self._items_iter: Any = None
        self._initialized = False

    @property
    def last_evaluated_key(self) -> dict[str, Any] | None:
        """The last evaluated key for pagination.

        Returns None if all results have been fetched.
        """
        if self._query_result is None:
            return None
        result: dict[str, Any] | None = self._query_result.last_evaluated_key
        return result

    def _build_query(self) -> Any:
        """Build the underlying QueryResult."""
        from pydynox.query import QueryResult

        client = self._model_class._get_client()
        table = self._model_class._get_table()

        # Build key condition expression
        # names: {attr_name: placeholder} - we need to track this for building expression
        # then convert to {placeholder: attr_name} for DynamoDB
        names: dict[str, str] = {}
        values: dict[str, Any] = {}

        # Build hash key conditions (all required)
        key_conditions: list[str] = []
        for i, attr_name in enumerate(self._hash_keys):
            name_placeholder = f"#gsi_hk{i}"
            value_placeholder = f":gsi_hkv{i}"
            names[attr_name] = name_placeholder
            values[value_placeholder] = self._hash_key_values[attr_name]
            key_conditions.append(f"{name_placeholder} = {value_placeholder}")

        key_condition = " AND ".join(key_conditions)

        # Add range key condition if provided
        if self._range_key_condition is not None:
            rk_expr = self._range_key_condition.serialize(names, values)
            key_condition = f"{key_condition} AND {rk_expr}"

        # Build filter expression if provided
        filter_expr = None
        if self._filter_condition is not None:
            filter_expr = self._filter_condition.serialize(names, values)

        # Convert names to DynamoDB format: {placeholder: attr_name}
        attr_names = {placeholder: attr_name for attr_name, placeholder in names.items()}

        return QueryResult(
            client._client,
            table,
            key_condition,
            filter_expression=filter_expr,
            expression_attribute_names=attr_names if attr_names else None,
            expression_attribute_values=values if values else None,
            limit=self._limit,
            scan_index_forward=self._scan_index_forward,
            index_name=self._index_name,
            last_evaluated_key=self._start_key,
            acquire_rcu=client._acquire_rcu,
        )

    def __iter__(self) -> GSIQueryResult[M]:
        return self

    def __next__(self) -> M:
        # Initialize on first iteration
        if not self._initialized:
            self._query_result = self._build_query()
            self._items_iter = iter(self._query_result)
            self._initialized = True

        # Get next item from underlying query
        item = next(self._items_iter)

        # Convert to model instance
        instance = self._model_class.from_dict(item)

        # Run after_load hooks
        skip = (
            self._model_class.model_config.skip_hooks
            if hasattr(self._model_class, "model_config")
            else False
        )
        if not skip:
            from pydynox.hooks import HookType

            instance._run_hooks(HookType.AFTER_LOAD)

        return instance
