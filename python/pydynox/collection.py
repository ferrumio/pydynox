"""Collection - multi-entity query for single-table design."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, NamedTuple, TypeVar

from pydynox.hooks import HookType

if TYPE_CHECKING:
    from pydynox.model import Model

M = TypeVar("M", bound="Model")


class _QueryParams(NamedTuple):
    key_condition: str
    attr_names: dict[str, str]
    attr_values: dict[str, Any]


class CollectionResult:
    """Result of a Collection query with typed access to each entity type.

    Access results by model name (lowercase, pluralized):
    - result.users -> list[User]
    - result.orders -> list[Order]

    Or use get() for explicit type:
    - result.get(User) -> list[User]
    """

    def __init__(self, models: list[type[M]], items: list[dict[str, Any]]) -> None:
        self._models = {m.__name__: m for m in models}
        self._items_by_type: dict[str, list[Any]] = {m.__name__: [] for m in models}

        # Sort items by discriminator value
        for item in items:
            for model_name, model_cls in self._models.items():
                disc_attr = model_cls._discriminator_attr
                if disc_attr and item.get(disc_attr) == model_name:
                    instance = model_cls.from_dict(item)
                    skip = getattr(model_cls.model_config, "skip_hooks", False)
                    if not skip:
                        instance._run_hooks(HookType.AFTER_LOAD)
                    self._items_by_type[model_name].append(instance)
                    break

    def get(self, model_class: type[M]) -> list[M]:
        """Get all items of a specific model type.

        Args:
            model_class: The model class to get items for.

        Returns:
            List of model instances.

        Example:
            >>> users = result.get(User)
            >>> orders = result.get(Order)
        """
        return self._items_by_type.get(model_class.__name__, [])

    def __getattr__(self, name: str) -> list[Any]:
        """Access results by pluralized model name.

        Example:
            >>> result.users  # list[User]
            >>> result.orders  # list[Order]
        """
        # Try to match pluralized name to model
        for model_name in self._items_by_type:
            # Simple pluralization: User -> users, Order -> orders
            plural = model_name.lower() + "s"
            if name == plural:
                return self._items_by_type[model_name]

        raise AttributeError(f"'{type(self).__name__}' has no attribute '{name}'")

    def __repr__(self) -> str:
        counts = ", ".join(f"{k}: {len(v)}" for k, v in self._items_by_type.items())
        return f"CollectionResult({counts})"


class Collection:
    """Group of Models that share the same table for multi-entity queries.

    Collection lets you query multiple entity types in one DynamoDB call.
    All models must share the same table and have a discriminator field.

    Example:
        >>> collection = Collection([User, Order, Address])
        >>> result = await collection.query(pk="USER#123")
        >>> result.users      # [User(...)]
        >>> result.orders     # [Order(...), Order(...)]
        >>> result.addresses  # [Address(...)]
    """

    def __init__(self, models: list[type[M]]) -> None:
        """Create a Collection from a list of Model classes.

        Args:
            models: List of Model classes that share the same table.

        Raises:
            ValueError: If models don't share the same table or lack discriminator.
        """
        if not models:
            raise ValueError("Collection requires at least one model")

        self._models = models
        self._validate_models()

    def _validate_models(self) -> None:
        """Validate all models share table and have discriminator."""
        tables = set()
        for model in self._models:
            # Check table
            if not hasattr(model, "model_config"):
                raise ValueError(f"Model {model.__name__} has no model_config")
            tables.add(model.model_config.table)

            # Check discriminator
            if not model._discriminator_attr:
                raise ValueError(
                    f"Model {model.__name__} has no discriminator field. "
                    "Add a StringAttribute with discriminator=True."
                )

        if len(tables) > 1:
            raise ValueError(f"All models must share the same table. Found: {tables}")

    def _get_table(self) -> str:
        """Get the shared table name."""
        return self._models[0].model_config.table

    def _get_client(self) -> Any:
        """Get the DynamoDB client from the first model."""
        return self._models[0]._get_client()

    def _build_collection_query_params(
        self,
        pk: str | None = None,
        sk_begins_with: str | None = None,
        **kwargs: Any,
    ) -> _QueryParams:
        """Build query parameters for collection query."""
        # Resolve partition key from template if needed
        partition_key = pk
        if partition_key is None and kwargs:
            partition_key = self._resolve_pk_from_template(kwargs)

        if partition_key is None:
            raise ValueError("pk is required")

        # Build key condition
        pk_attr = self._models[0]._partition_key
        if pk_attr is None:
            raise ValueError("Model has no partition key")

        names: dict[str, str] = {"#pk": pk_attr}
        values: dict[str, Any] = {":pkv": partition_key}

        key_condition = "#pk = :pkv"

        # Add sk_begins_with if provided
        if sk_begins_with:
            sk_attr = self._models[0]._sort_key
            if sk_attr:
                names["#sk"] = sk_attr
                values[":skprefix"] = sk_begins_with
                key_condition += " AND begins_with(#sk, :skprefix)"

        return _QueryParams(
            key_condition=key_condition,
            attr_names=names,
            attr_values=values,
        )

    async def query(
        self,
        pk: str | None = None,
        index: str | None = None,
        sk_begins_with: str | None = None,
        limit: int | None = None,
        consistent_read: bool = False,
        **kwargs: Any,
    ) -> CollectionResult:
        """Query all entity types by partition key.

        Args:
            pk: Partition key value.
            index: GSI name to query (optional).
            sk_begins_with: Filter by sort key prefix (optional).
            limit: Max items to return.
            consistent_read: Use strongly consistent read.
            **kwargs: Template placeholder values.

        Returns:
            CollectionResult with typed access to each entity type.

        Example:
            >>> result = await collection.query(pk="USER#123")
            >>> result.users   # [User(...)]
            >>> result.orders  # [Order(...)]
        """
        client = self._get_client()
        table = self._get_table()

        # Build query parameters
        params = self._build_collection_query_params(pk=pk, sk_begins_with=sk_begins_with, **kwargs)

        # Execute query and collect all items
        query_result = client.query(
            table,
            key_condition_expression=params.key_condition,
            expression_attribute_names=params.attr_names,
            expression_attribute_values=params.attr_values,
            index_name=index,
            limit=limit,
            consistent_read=consistent_read,
        )

        items = [item async for item in query_result]

        return CollectionResult(self._models, items)

    def sync_query(
        self,
        pk: str | None = None,
        index: str | None = None,
        sk_begins_with: str | None = None,
        limit: int | None = None,
        consistent_read: bool = False,
        **kwargs: Any,
    ) -> CollectionResult:
        """Query all entity types by partition key (sync).

        Args:
            pk: Partition key value.
            index: GSI name to query (optional).
            sk_begins_with: Filter by sort key prefix (optional).
            limit: Max items to return.
            consistent_read: Use strongly consistent read.
            **kwargs: Template placeholder values.

        Returns:
            CollectionResult with typed access to each entity type.

        Example:
            >>> result = collection.sync_query(pk="USER#123")
            >>> result.users   # [User(...)]
            >>> result.orders  # [Order(...)]
        """
        client = self._get_client()
        table = self._get_table()

        # Build query parameters
        params = self._build_collection_query_params(pk=pk, sk_begins_with=sk_begins_with, **kwargs)

        # Execute query and collect all items
        query_result = client.sync_query(
            table,
            key_condition_expression=params.key_condition,
            expression_attribute_names=params.attr_names,
            expression_attribute_values=params.attr_values,
            index_name=index,
            limit=limit,
            consistent_read=consistent_read,
        )

        items = list(query_result)

        return CollectionResult(self._models, items)

    def _resolve_pk_from_template(self, kwargs: dict[str, Any]) -> str | None:
        """Try to resolve pk from template placeholders."""
        model = self._models[0]
        pk_attr_name = model._partition_key
        if pk_attr_name is None:
            return None

        pk_attr = model._attributes.get(pk_attr_name)
        if pk_attr is None:
            return None

        if not (hasattr(pk_attr, "has_template") and pk_attr.has_template):
            return None

        # Cast to template-aware attribute for type checker
        template_attr = pk_attr

        # Build from template
        values = {}
        for placeholder in template_attr.placeholders:  # type: ignore[union-attr]
            if placeholder not in kwargs:
                return None
            values[placeholder] = kwargs[placeholder]

        return template_attr.build_key(values)  # type: ignore[union-attr]

    def __repr__(self) -> str:
        names = ", ".join(m.__name__ for m in self._models)
        return f"Collection([{names}])"
