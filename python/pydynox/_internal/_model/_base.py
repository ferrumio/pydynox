"""Base Model class with metaclass and core functionality."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar, TypeVar

from pydynox._internal._indexes import GlobalSecondaryIndex, LocalSecondaryIndex
from pydynox.attributes import Attribute
from pydynox.client import DynamoDBClient
from pydynox.config import ModelConfig, get_default_client
from pydynox.generators import generate_value, is_auto_generate
from pydynox.hooks import HookType
from pydynox.size import ItemSize, calculate_item_size

if TYPE_CHECKING:
    from pydynox._internal._metrics import MetricsStorage

M = TypeVar("M", bound="ModelBase")


class ModelMeta(type):
    """Metaclass that collects attributes and builds schema."""

    _attributes: dict[str, Attribute[Any]]
    _hash_key: str | None
    _range_key: str | None
    _hooks: dict[HookType, list[Any]]
    _indexes: dict[str, GlobalSecondaryIndex[Any]]
    _local_indexes: dict[str, LocalSecondaryIndex[Any]]
    _metrics_storage: "MetricsStorage"

    def __new__(mcs, name: str, bases: tuple[type, ...], namespace: dict[str, Any]) -> ModelMeta:
        attributes: dict[str, Attribute[Any]] = {}
        hash_key: str | None = None
        range_key: str | None = None
        hooks: dict[HookType, list[Any]] = {hook_type: [] for hook_type in HookType}
        indexes: dict[str, GlobalSecondaryIndex[Any]] = {}
        local_indexes: dict[str, LocalSecondaryIndex[Any]] = {}

        for base in bases:
            base_attrs = getattr(base, "_attributes", None)
            if base_attrs is not None:
                attributes.update(base_attrs)
            base_hash_key = getattr(base, "_hash_key", None)
            if base_hash_key:
                hash_key = base_hash_key
            base_range_key = getattr(base, "_range_key", None)
            if base_range_key:
                range_key = base_range_key
            base_hooks = getattr(base, "_hooks", None)
            if base_hooks is not None:
                for hook_type, hook_list in base_hooks.items():
                    hooks[hook_type].extend(hook_list)
            base_indexes = getattr(base, "_indexes", None)
            if base_indexes is not None:
                indexes.update(base_indexes)
            base_local_indexes = getattr(base, "_local_indexes", None)
            if base_local_indexes is not None:
                local_indexes.update(base_local_indexes)

        for attr_name, attr_value in namespace.items():
            if isinstance(attr_value, Attribute):
                attr_value.attr_name = attr_name
                attributes[attr_name] = attr_value

                if attr_value.hash_key:
                    hash_key = attr_name
                if attr_value.range_key:
                    range_key = attr_name

            if callable(attr_value) and hasattr(attr_value, "_hook_type"):
                hooks[getattr(attr_value, "_hook_type")].append(attr_value)

            if isinstance(attr_value, GlobalSecondaryIndex):
                indexes[attr_name] = attr_value

            if isinstance(attr_value, LocalSecondaryIndex):
                local_indexes[attr_name] = attr_value

        cls = super().__new__(mcs, name, bases, namespace)

        cls._attributes = attributes
        cls._hash_key = hash_key
        cls._range_key = range_key
        cls._hooks = hooks
        cls._indexes = indexes
        cls._local_indexes = local_indexes

        # Each Model class gets its own metrics storage
        from pydynox._internal._metrics import MetricsStorage

        cls._metrics_storage = MetricsStorage()

        for idx in indexes.values():
            idx._bind_to_model(cls)

        for idx in local_indexes.values():
            idx._bind_to_model(cls)

        return cls


class ModelBase(metaclass=ModelMeta):
    """Base class with core Model functionality.

    This contains __init__, to_dict, from_dict, and helper methods.
    CRUD operations are added by the Model class in model.py.
    """

    _attributes: ClassVar[dict[str, Attribute[Any]]]
    _hash_key: ClassVar[str | None]
    _range_key: ClassVar[str | None]
    _hooks: ClassVar[dict[HookType, list[Any]]]
    _indexes: ClassVar[dict[str, GlobalSecondaryIndex[Any]]]
    _local_indexes: ClassVar[dict[str, LocalSecondaryIndex[Any]]]
    _client_instance: ClassVar[DynamoDBClient | None] = None
    _metrics_storage: ClassVar["MetricsStorage"]

    model_config: ClassVar[ModelConfig]

    def __init__(self, **kwargs: Any) -> None:
        for attr_name, attr in self._attributes.items():
            if attr_name in kwargs:
                setattr(self, attr_name, kwargs[attr_name])
            elif attr.default is not None:
                if is_auto_generate(attr.default):
                    setattr(self, attr_name, None)
                else:
                    setattr(self, attr_name, attr.default)
            elif not attr.null:
                raise ValueError(f"Attribute '{attr_name}' is required")
            else:
                setattr(self, attr_name, None)

    def _apply_auto_generate(self) -> None:
        """Apply auto-generate strategies to None attributes."""
        for attr_name, attr in self._attributes.items():
            if attr.default is not None and is_auto_generate(attr.default):
                current_value = getattr(self, attr_name, None)
                if current_value is None:
                    generated = generate_value(attr.default)
                    setattr(self, attr_name, generated)

    @classmethod
    def _get_client(cls) -> DynamoDBClient:
        """Get the DynamoDB client for this model."""
        if cls._client_instance is not None:
            return cls._client_instance

        if hasattr(cls, "model_config") and cls.model_config.client is not None:
            cls._client_instance = cls.model_config.client
            cls._apply_hot_partition_overrides()
            return cls._client_instance

        default = get_default_client()
        if default is not None:
            cls._client_instance = default
            cls._apply_hot_partition_overrides()
            return cls._client_instance

        raise ValueError(
            f"No client configured for {cls.__name__}. "
            "Either pass client to ModelConfig or call pydynox.set_default_client()"
        )

    @classmethod
    def _apply_hot_partition_overrides(cls) -> None:
        """Apply hot partition threshold overrides from ModelConfig."""
        if cls._client_instance is None:
            return

        diagnostics = cls._client_instance.diagnostics
        if diagnostics is None:
            return

        if not hasattr(cls, "model_config"):
            return

        writes = getattr(cls.model_config, "hot_partition_writes", None)
        reads = getattr(cls.model_config, "hot_partition_reads", None)

        if writes is not None or reads is not None:
            table = cls.model_config.table
            diagnostics.set_table_thresholds(table, writes_threshold=writes, reads_threshold=reads)

    @classmethod
    def _get_table(cls) -> str:
        """Get the table name from model_config."""
        if not hasattr(cls, "model_config"):
            raise ValueError(f"Model {cls.__name__} must define model_config")
        return cls.model_config.table

    def _should_skip_hooks(self, skip_hooks: bool | None) -> bool:
        if skip_hooks is not None:
            return skip_hooks
        if hasattr(self, "model_config"):
            return self.model_config.skip_hooks
        return False

    def _run_hooks(self, hook_type: HookType) -> None:
        for hook in self._hooks.get(hook_type, []):
            hook(self)

    def _get_key(self) -> dict[str, Any]:
        key = {}
        if self._hash_key:
            key[self._hash_key] = getattr(self, self._hash_key)
        if self._range_key:
            key[self._range_key] = getattr(self, self._range_key)
        return key

    def to_dict(self) -> dict[str, Any]:
        """Convert the model to a dict."""
        result = {}
        for attr_name, attr in self._attributes.items():
            value = getattr(self, attr_name, None)
            if value is not None:
                result[attr_name] = attr.serialize(value)
        return result

    def calculate_size(self, detailed: bool = False) -> ItemSize:
        """Calculate the size of this item in bytes."""
        item = self.to_dict()
        return calculate_item_size(item, detailed=detailed)

    @classmethod
    def from_dict(cls: type[M], data: dict[str, Any]) -> M:
        """Create a model instance from a dict."""
        deserialized = {}
        for attr_name, value in data.items():
            if attr_name in cls._attributes:
                deserialized[attr_name] = cls._attributes[attr_name].deserialize(value)
            else:
                deserialized[attr_name] = value
        return cls(**deserialized)

    def __repr__(self) -> str:
        attrs = ", ".join(f"{k}={v!r}" for k, v in self.to_dict().items())
        return f"{self.__class__.__name__}({attrs})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, self.__class__):
            return False
        return self._get_key() == other._get_key()

    @classmethod
    def _extract_key_from_kwargs(
        cls, kwargs: dict[str, Any]
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """Split kwargs into key attributes and updates."""
        if cls._hash_key is None:
            raise ValueError(f"Model {cls.__name__} has no hash_key defined")

        key: dict[str, Any] = {}
        updates: dict[str, Any] = {}

        for attr_name, value in kwargs.items():
            if attr_name == cls._hash_key:
                key[attr_name] = value
            elif attr_name == cls._range_key:
                key[attr_name] = value
            else:
                updates[attr_name] = value

        if cls._hash_key not in key:
            raise ValueError(f"Missing required hash_key: {cls._hash_key}")

        if cls._range_key is not None and cls._range_key not in key:
            raise ValueError(f"Missing required range_key: {cls._range_key}")

        return key, updates
