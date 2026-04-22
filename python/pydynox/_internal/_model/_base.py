"""Base Model class with metaclass and core functionality."""

from __future__ import annotations

import warnings
from typing import TYPE_CHECKING, Any, ClassVar, Protocol, TypeVar, cast

from pydynox._internal._indexes import GlobalSecondaryIndex, LocalSecondaryIndex
from pydynox.attributes import Attribute
from pydynox.attributes.special import JSONAttribute
from pydynox.config import DynamoConfig, get_default_client
from pydynox.generators import generate_value, is_auto_generate
from pydynox.hooks import HookType
from pydynox.size import ItemSize, calculate_item_size

if TYPE_CHECKING:
    from pydynox._internal._metrics import MetricsStorage
    from pydynox.client import DynamoDBClient

M = TypeVar("M", bound="ModelBase")


_LEGACY_CONFIG_WARNED: set[int] = set()


def _warn_legacy_model_config(cls: type) -> None:
    """Emit a DeprecationWarning for a class that uses the legacy
    ``model_config`` attribute. Fires at most once per class to keep
    logs quiet on hot paths.
    """
    key = id(cls)
    if key in _LEGACY_CONFIG_WARNED:
        return
    _LEGACY_CONFIG_WARNED.add(key)
    warnings.warn(
        f"{cls.__name__}: `model_config = ModelConfig(...)` is deprecated; "
        "rename to `dynamodb_config: ClassVar[DynamoConfig] = DynamoConfig(...)`. "
        "See docs/refactor/pydantic-model/01-dynamoconfig-rename.md.",
        DeprecationWarning,
        stacklevel=3,
    )


class _TemplateAttr(Protocol):
    """Protocol for attributes with template support."""

    has_template: bool
    placeholders: list[str]

    def build_key(self, values: dict[str, Any]) -> str: ...


class ModelMeta(type):
    """Metaclass that collects attributes and builds schema."""

    _attributes: dict[str, Attribute[Any]]
    _partition_key: str | None
    _sort_key: str | None
    _discriminator_attr: str | None
    _discriminator_registry: dict[str, type]
    _hooks: dict[HookType, list[Any]]
    _indexes: dict[str, GlobalSecondaryIndex[Any]]
    _local_indexes: dict[str, LocalSecondaryIndex[Any]]
    _metrics_storage: "MetricsStorage"
    _py_to_dynamo: dict[str, str]
    _dynamo_to_py: dict[str, str]

    def __new__(mcs, name: str, bases: tuple[type, ...], namespace: dict[str, Any]) -> ModelMeta:
        attributes: dict[str, Attribute[Any]] = {}
        partition_key: str | None = None
        sort_key: str | None = None
        discriminator_attr: str | None = None
        discriminator_registry: dict[str, type] = {}
        hooks: dict[HookType, list[Any]] = {hook_type: [] for hook_type in HookType}
        indexes: dict[str, GlobalSecondaryIndex[Any]] = {}
        local_indexes: dict[str, LocalSecondaryIndex[Any]] = {}

        for base in bases:
            base_attrs = getattr(base, "_attributes", None)
            if base_attrs is not None:
                attributes.update(base_attrs)
            else:
                # Base class without metaclass - collect attributes from __dict__
                for attr_name, attr_value in base.__dict__.items():
                    if isinstance(attr_value, Attribute):
                        attr_value.attr_name = attr_name
                        attributes[attr_name] = attr_value
                        if attr_value.partition_key:
                            partition_key = attr_name
                        if attr_value.sort_key:
                            sort_key = attr_name
                        if getattr(attr_value, "discriminator", False):
                            discriminator_attr = attr_name

            base_partition_key = getattr(base, "_partition_key", None)
            if base_partition_key:
                partition_key = base_partition_key
            base_sort_key = getattr(base, "_sort_key", None)
            if base_sort_key:
                sort_key = base_sort_key
            base_discriminator = getattr(base, "_discriminator_attr", None)
            if base_discriminator:
                discriminator_attr = base_discriminator
            base_registry = getattr(base, "_discriminator_registry", None)
            if base_registry is not None:
                discriminator_registry.update(base_registry)
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

                if attr_value.partition_key:
                    partition_key = attr_name
                if attr_value.sort_key:
                    sort_key = attr_name
                if getattr(attr_value, "discriminator", False):
                    discriminator_attr = attr_name

            if callable(attr_value) and hasattr(attr_value, "_hook_type"):
                hooks[getattr(attr_value, "_hook_type")].append(attr_value)

            if isinstance(attr_value, GlobalSecondaryIndex):
                indexes[attr_name] = attr_value

            if isinstance(attr_value, LocalSecondaryIndex):
                local_indexes[attr_name] = attr_value

        cls = super().__new__(mcs, name, bases, namespace)

        cls._attributes = attributes
        cls._partition_key = partition_key
        cls._sort_key = sort_key
        cls._discriminator_attr = discriminator_attr
        cls._discriminator_registry = discriminator_registry
        cls._hooks = hooks
        cls._indexes = indexes
        cls._local_indexes = local_indexes

        # Build alias lookup dicts
        py_to_dynamo: dict[str, str] = {}
        dynamo_to_py: dict[str, str] = {}
        for attr_name, attr in attributes.items():
            alias = getattr(attr, "alias", None)
            if alias is not None:
                py_to_dynamo[attr_name] = alias
                dynamo_to_py[alias] = attr_name
        cls._py_to_dynamo = py_to_dynamo
        cls._dynamo_to_py = dynamo_to_py

        # Register this class in ALL parent discriminator registries
        if discriminator_attr and name != "ModelBase" and name != "Model":
            # Walk up the inheritance chain and register in all registries
            for base in bases:
                current = base
                while current is not None:
                    base_registry = getattr(current, "_discriminator_registry", None)
                    if base_registry is not None:
                        base_registry[name] = cls
                    # Move to parent
                    parent_bases = getattr(current, "__bases__", ())
                    current = None
                    for parent in parent_bases:
                        if hasattr(parent, "_discriminator_registry"):
                            current = parent
                            break
            # Also register in own registry for subclasses
            discriminator_registry[name] = cls

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
    _partition_key: ClassVar[str | None]
    _sort_key: ClassVar[str | None]
    _discriminator_attr: ClassVar[str | None]
    _discriminator_registry: ClassVar[dict[str, type]]
    _hooks: ClassVar[dict[HookType, list[Any]]]
    _indexes: ClassVar[dict[str, GlobalSecondaryIndex[Any]]]
    _local_indexes: ClassVar[dict[str, LocalSecondaryIndex[Any]]]
    _client_instance: ClassVar[DynamoDBClient | None] = None
    _metrics_storage: ClassVar["MetricsStorage"]
    _py_to_dynamo: ClassVar[dict[str, str]]
    _dynamo_to_py: ClassVar[dict[str, str]]

    # New canonical name. Subclasses should set this instead of
    # ``model_config``. The legacy name keeps working (see
    # :meth:`_get_config`) with a one-time DeprecationWarning per class.
    dynamodb_config: ClassVar[DynamoConfig]

    # Change tracking
    _original: dict[str, Any] | None
    _changed: set[str]
    _json_snapshots: dict[str, str | None]

    def __init__(self, **kwargs: Any) -> None:
        # Initialize change tracking (must be first to avoid __setattr__ issues)
        object.__setattr__(self, "_original", None)
        object.__setattr__(self, "_changed", set())
        object.__setattr__(self, "_json_snapshots", {})
        # First pass: set all regular attributes
        for attr_name, attr in self._attributes.items():
            # Skip template keys in first pass - they'll be built later
            if hasattr(attr, "has_template") and attr.has_template:
                continue

            if attr_name in kwargs:
                setattr(self, attr_name, kwargs[attr_name])
            elif attr.default is not None:
                if is_auto_generate(attr.default):
                    setattr(self, attr_name, None)
                else:
                    setattr(self, attr_name, attr.default)
            elif attr.required:
                raise ValueError(f"Attribute '{attr_name}' is required")
            else:
                setattr(self, attr_name, None)

        # Second pass: build template keys from other attributes
        for attr_name, attr in self._attributes.items():
            if not (hasattr(attr, "has_template") and attr.has_template):
                continue

            tattr = cast(_TemplateAttr, attr)

            # If user explicitly passed the key value, validate it matches template
            if attr_name in kwargs:
                # Allow direct assignment for now (e.g., from_dict)
                setattr(self, attr_name, kwargs[attr_name])
            else:
                # Build key from template using other attribute values
                values = {k: getattr(self, k, None) for k in tattr.placeholders}
                # Check if all placeholders have values
                missing = [k for k, v in values.items() if v is None]
                if missing:
                    # Can't build yet - will be built in _apply_auto_generate or save
                    setattr(self, attr_name, None)
                else:
                    setattr(self, attr_name, tattr.build_key(values))

    def __setattr__(self, name: str, value: Any) -> None:
        """Track attribute changes for smart updates."""
        # Skip tracking for internal attributes
        if name.startswith("_"):
            object.__setattr__(self, name, value)
            return

        # Track changes if we have an original snapshot
        original = object.__getattribute__(self, "_original")
        if original is not None and name in self._attributes:
            changed = object.__getattribute__(self, "_changed")
            old_value = original.get(name)
            if value != old_value:
                changed.add(name)
            elif name in changed:
                changed.discard(name)

        object.__setattr__(self, name, value)

    @property
    def is_dirty(self) -> bool:
        """Check if any attributes have changed since loading from DB.

        Returns:
            True if any attributes were modified, False otherwise.

        Example:
            >>> user = await User.get(pk="USER#1")
            >>> print(user.is_dirty)  # False
            >>> user.name = "New Name"
            >>> print(user.is_dirty)  # True
        """
        return len(self._changed) > 0

    @property
    def changed_fields(self) -> list[str]:
        """Get list of attribute names that changed since loading from DB.

        Returns:
            List of changed attribute names.

        Example:
            >>> user = await User.get(pk="USER#1")
            >>> user.name = "New Name"
            >>> user.email = "new@example.com"
            >>> print(user.changed_fields)  # ["name", "email"]
        """
        return list(self._changed)

    def _reset_change_tracking(self) -> None:
        """Reset change tracking after save. Stores current state as original."""
        self._original = {name: getattr(self, name) for name in self._attributes}
        self._changed = set()
        self._build_json_snapshots()

    def _build_json_snapshots(self) -> None:
        """Build JSON string snapshots for typed JSONAttributes.

        Used to detect in-place mutations on typed JSON objects
        (e.g., model.payload.score = 0.99) that bypass __setattr__.
        """
        snapshots: dict[str, str | None] = {}
        for attr_name, attr in self._attributes.items():
            if isinstance(attr, JSONAttribute) and attr.model_class is not None:
                value = getattr(self, attr_name, None)
                snapshots[attr_name] = attr.serialize(value)
        self._json_snapshots = snapshots

    def _detect_json_mutations(self) -> None:
        """Detect in-place mutations on typed JSONAttributes.

        Compares current serialized JSON against stored snapshots.
        Adds mutated attributes to _changed set.
        """
        if not self._json_snapshots:
            return
        for attr_name, old_json in self._json_snapshots.items():
            attr = self._attributes[attr_name]
            current_value = getattr(self, attr_name, None)
            current_json = attr.serialize(current_value)
            if current_json != old_json:
                self._changed.add(attr_name)

    def _apply_auto_generate(self) -> None:
        """Apply auto-generate strategies to None attributes."""
        for attr_name, attr in self._attributes.items():
            if attr.default is not None and is_auto_generate(attr.default):
                current_value = getattr(self, attr_name, None)
                if current_value is None:
                    generated = generate_value(attr.default)
                    setattr(self, attr_name, generated)

        # Rebuild template keys after auto-generate (placeholders may now have values)
        self._build_template_keys()

    def _build_template_keys(self) -> None:
        """Build template key values from placeholder attributes."""
        for attr_name, attr in self._attributes.items():
            if not (hasattr(attr, "has_template") and attr.has_template):
                continue

            tattr = cast(_TemplateAttr, attr)

            # Collect values for all placeholders
            values = {}
            for placeholder in tattr.placeholders:
                val = getattr(self, placeholder, None)
                if val is None:
                    raise ValueError(f"Cannot build {attr_name}: missing value for '{placeholder}'")
                values[placeholder] = val

            # Build and set the key
            setattr(self, attr_name, tattr.build_key(values))

    @classmethod
    def _get_config(cls) -> DynamoConfig | None:
        """Return the resolved DynamoDB config for this model, if any.

        Resolution order:

        1. ``cls.dynamodb_config`` — the canonical attribute.
        2. ``cls.model_config`` — legacy name, kept for back-compat.
           Emits a one-time :class:`DeprecationWarning` per class pointing
           users at ``dynamodb_config``.
        3. ``None`` — caller is responsible for raising or falling back.

        The legacy branch requires the value to be a :class:`DynamoConfig`
        instance so that a pydantic ``ConfigDict`` on a subclass cannot be
        mistaken for pydynox configuration (relevant once
        ``PydanticModel`` lands in PR 4).
        """
        new = getattr(cls, "dynamodb_config", None)
        if isinstance(new, DynamoConfig):
            return new

        legacy = getattr(cls, "model_config", None)
        if isinstance(legacy, DynamoConfig):
            _warn_legacy_model_config(cls)
            return legacy

        return None

    @classmethod
    def _get_client(cls) -> DynamoDBClient:
        """Get the DynamoDB client for this model."""
        if cls._client_instance is not None:
            return cls._client_instance

        config = cls._get_config()
        if config is not None and config.client is not None:
            cls._client_instance = config.client
            cls._apply_hot_partition_overrides()
            return cls._client_instance

        default = get_default_client()
        if default is not None:
            cls._client_instance = default
            cls._apply_hot_partition_overrides()
            return cls._client_instance

        raise ValueError(
            f"No client configured for {cls.__name__}. "
            "Either pass client to DynamoConfig or call pydynox.set_default_client()"
        )

    @classmethod
    def _apply_hot_partition_overrides(cls) -> None:
        """Apply hot partition threshold overrides from the model config."""
        if cls._client_instance is None:
            return

        diagnostics = cls._client_instance.diagnostics
        if diagnostics is None:
            return

        config = cls._get_config()
        if config is None:
            return

        writes = config.hot_partition_writes
        reads = config.hot_partition_reads

        if writes is not None or reads is not None:
            diagnostics.set_table_thresholds(
                config.table, writes_threshold=writes, reads_threshold=reads
            )

    @classmethod
    def _get_table(cls) -> str:
        """Get the table name from the model config."""
        config = cls._get_config()
        if config is None:
            raise ValueError(f"Model {cls.__name__} must define dynamodb_config")
        return config.table

    @classmethod
    def _config_skip_hooks(cls) -> bool:
        """Return ``skip_hooks`` from DynamoConfig, or False when unconfigured."""
        config = cls._get_config()
        if config is not None:
            return config.skip_hooks
        return False

    def _should_skip_hooks(self, skip_hooks: bool | None) -> bool:
        if skip_hooks is not None:
            return skip_hooks
        return type(self)._config_skip_hooks()

    @classmethod
    def _run_after_load_hook(cls, instance: M) -> None:
        """Run AFTER_LOAD unless DynamoConfig has ``skip_hooks`` set."""
        if not cls._config_skip_hooks():
            instance._run_hooks(HookType.AFTER_LOAD)

    @classmethod
    def _run_after_load_hooks_batch(cls, instances: list[M]) -> None:
        """Run AFTER_LOAD on instances unless the model config suppresses hooks."""
        if cls._config_skip_hooks():
            return
        for instance in instances:
            instance._run_hooks(HookType.AFTER_LOAD)

    def _run_hooks(self, hook_type: HookType) -> None:
        for hook in self._hooks.get(hook_type, []):
            hook(self)

    def _get_key(self) -> dict[str, Any]:
        key = {}
        if self._partition_key:
            dynamo_name = self._py_to_dynamo.get(self._partition_key, self._partition_key)
            key[dynamo_name] = getattr(self, self._partition_key)
        if self._sort_key:
            dynamo_name = self._py_to_dynamo.get(self._sort_key, self._sort_key)
            key[dynamo_name] = getattr(self, self._sort_key)
        return key

    def to_dict(self) -> dict[str, Any]:
        """Convert the model to a dict.

        Uses alias names for DynamoDB keys when defined.
        """
        result = {}
        for attr_name, attr in self._attributes.items():
            dynamo_name = self._py_to_dynamo.get(attr_name, attr_name)
            value = getattr(self, attr_name, None)
            if value is not None:
                result[dynamo_name] = attr.serialize(value)
            # Auto-set discriminator to class name
            elif getattr(attr, "discriminator", False):
                result[dynamo_name] = self.__class__.__name__
        return result

    def calculate_size(self, detailed: bool = False) -> ItemSize:
        """Calculate the size of this item in bytes."""
        item = self.to_dict()
        return calculate_item_size(item, detailed=detailed)

    @classmethod
    def from_dict(cls: type[M], data: dict[str, Any]) -> M:
        """Create a model instance from a dict.

        Translates DynamoDB alias names back to Python attribute names.
        Stores the original data for change tracking, enabling smart updates
        that only send changed fields to DynamoDB.

        If the model has a discriminator field, returns the correct subclass.
        """
        # Check if we should return a subclass based on discriminator
        target_cls: type[M] = cls

        if cls._discriminator_attr and cls._discriminator_registry:
            # Discriminator value might be under alias or python name
            disc_dynamo = cls._py_to_dynamo.get(cls._discriminator_attr, cls._discriminator_attr)
            type_value = data.get(cls._discriminator_attr) or data.get(disc_dynamo)
            if type_value and type_value in cls._discriminator_registry:
                target_cls = cast(type[M], cls._discriminator_registry[type_value])

        # Translate alias keys to python names
        translated: dict[str, Any] = {}
        for key, value in data.items():
            py_name = target_cls._dynamo_to_py.get(key, key)
            translated[py_name] = value

        deserialized = {}
        for attr_name, value in translated.items():
            if attr_name in target_cls._attributes:
                deserialized[attr_name] = target_cls._attributes[attr_name].deserialize(value)
            else:
                deserialized[attr_name] = value
        instance = target_cls(**deserialized)
        # Store original for change tracking with Python names and deserialized values
        # so __setattr__ can compare correctly (it looks up by Python attr name)
        instance._original = deserialized.copy()
        instance._changed = set()
        instance._build_json_snapshots()
        return instance

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
        """Split kwargs into key attributes and updates.

        Keys use alias names for DynamoDB. Updates use Python names.
        """
        if cls._partition_key is None:
            raise ValueError(f"Model {cls.__name__} has no partition_key defined")

        key: dict[str, Any] = {}
        updates: dict[str, Any] = {}

        for attr_name, value in kwargs.items():
            if attr_name == cls._partition_key:
                dynamo_name = cls._py_to_dynamo.get(attr_name, attr_name)
                key[dynamo_name] = value
            elif attr_name == cls._sort_key:
                dynamo_name = cls._py_to_dynamo.get(attr_name, attr_name)
                key[dynamo_name] = value
            else:
                updates[attr_name] = value

        if cls._partition_key not in kwargs:
            raise ValueError(f"Missing required partition_key: {cls._partition_key}")

        if cls._sort_key is not None and cls._sort_key not in kwargs:
            raise ValueError(f"Missing required sort_key: {cls._sort_key}")

        return key, updates
