"""Shared helpers for sync and async CRUD operations."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, TypeVar

from pydynox._internal._atomic import AtomicOp, serialize_atomic
from pydynox._internal._conditions import ConditionPath
from pydynox.exceptions import ItemTooLargeError
from pydynox.hooks import HookType

if TYPE_CHECKING:
    from pydynox.client import DynamoDBClient
    from pydynox.conditions import Condition
    from pydynox.model import Model

M = TypeVar("M", bound="Model")

# Type aliases for return types
SaveResult = tuple[
    "DynamoDBClient",
    str,
    dict[str, Any],
    str | None,
    dict[str, str] | None,
    dict[str, Any] | None,
    bool,
]
UpdateResult = tuple[
    "DynamoDBClient",
    str,
    dict[str, Any],
    str | None,
    str | None,
    dict[str, str] | None,
    dict[str, Any] | None,
    dict[str, Any] | None,
    bool,
]
UpdateByKeyResult = tuple[
    "DynamoDBClient",
    str,
    dict[str, Any],
    dict[str, Any],
    str | None,
    dict[str, str] | None,
    dict[str, Any] | None,
]
DeleteByKeyResult = tuple[
    "DynamoDBClient", str, dict[str, Any], str | None, dict[str, str] | None, dict[str, Any] | None
]


def prepare_get(
    cls: type[M], consistent_read: bool | None, keys: dict[str, Any]
) -> tuple[DynamoDBClient, str, dict[str, Any], bool]:
    """Prepare get operation. Returns (client, table, keys, use_consistent)."""
    client = cls._get_client()
    table = cls._get_table()

    use_consistent = consistent_read
    if use_consistent is None:
        use_consistent = getattr(cls.model_config, "consistent_read", False)

    return client, table, keys, use_consistent


def finalize_get(cls: type[M], item: dict[str, Any] | None) -> M | None:
    """Finalize get operation - convert to model and run hooks."""
    if item is None:
        return None

    instance = cls.from_dict(item)
    skip = cls.model_config.skip_hooks if hasattr(cls, "model_config") else False
    if not skip:
        instance._run_hooks(HookType.AFTER_LOAD)
    return instance


def prepare_save(self: Model, condition: Condition | None, skip_hooks: bool | None) -> SaveResult:
    """Prepare save operation.

    Returns (client, table, item, condition_expr, attr_names, attr_values, skip).
    """
    skip = self._should_skip_hooks(skip_hooks)

    if not skip:
        self._run_hooks(HookType.BEFORE_SAVE)

    self._apply_auto_generate()

    version_attr = self._get_version_attr_name()
    version_condition, new_version = self._build_version_condition()

    final_condition = condition
    if version_condition is not None:
        final_condition = (
            final_condition & version_condition if final_condition else version_condition
        )

    if version_attr is not None:
        setattr(self, version_attr, new_version)

    max_size = (
        getattr(self.model_config, "max_size", None) if hasattr(self, "model_config") else None
    )
    if max_size is not None:
        size = self.calculate_size()
        if size.bytes > max_size:
            raise ItemTooLargeError(
                size=size.bytes,
                max_size=max_size,
                item_key=self._get_key(),
            )

    client = self._get_client()
    table = self._get_table()
    item = self.to_dict()

    if final_condition is not None:
        names: dict[str, str] = {}
        values: dict[str, Any] = {}
        expr = final_condition.serialize(names, values)
        attr_names = {v: k for k, v in names.items()}
        return client, table, item, expr, attr_names, values, skip

    return client, table, item, None, None, None, skip


def finalize_save(self: Model, skip: bool) -> None:
    """Finalize save operation - run after hooks."""
    if not skip:
        self._run_hooks(HookType.AFTER_SAVE)


def prepare_delete(self: Model, condition: Condition | None, skip_hooks: bool | None) -> SaveResult:
    """Prepare delete. Returns (client, table, key, cond_expr, attr_names, attr_values, skip)."""
    skip = self._should_skip_hooks(skip_hooks)

    if not skip:
        self._run_hooks(HookType.BEFORE_DELETE)

    version_attr = self._get_version_attr_name()
    version_condition: Condition | None = None
    if version_attr is not None:
        current_version: int | None = getattr(self, version_attr, None)
        if current_version is not None:
            path = ConditionPath(path=[version_attr])
            version_condition = path == current_version

    final_condition = condition
    if version_condition is not None:
        final_condition = (
            final_condition & version_condition if final_condition else version_condition
        )

    client = self._get_client()
    table = self._get_table()
    key = self._get_key()

    if final_condition is not None:
        names: dict[str, str] = {}
        values: dict[str, Any] = {}
        expr = final_condition.serialize(names, values)
        attr_names = {v: k for k, v in names.items()}
        return client, table, key, expr, attr_names, values, skip

    return client, table, key, None, None, None, skip


def finalize_delete(self: Model, skip: bool) -> None:
    """Finalize delete operation - run after hooks."""
    if not skip:
        self._run_hooks(HookType.AFTER_DELETE)


def prepare_update(
    self: Model,
    atomic: list[AtomicOp] | None,
    condition: Condition | None,
    skip_hooks: bool | None,
    kwargs: dict[str, Any],
) -> UpdateResult:
    """Prepare update. Returns UpdateResult tuple."""
    skip = self._should_skip_hooks(skip_hooks)

    if not skip:
        self._run_hooks(HookType.BEFORE_UPDATE)

    client = self._get_client()
    table = self._get_table()
    key = self._get_key()

    if atomic:
        update_expr, names, values = serialize_atomic(atomic)
        attr_names = {v: k for k, v in names.items()}

        cond_expr = None
        if condition is not None:
            cond_names: dict[str, str] = dict(names)
            cond_expr = condition.serialize(cond_names, values)
            cond_attr_names = {v: k for k, v in cond_names.items()}
            attr_names = {**attr_names, **cond_attr_names}

        return (
            client,
            table,
            key,
            update_expr,
            cond_expr,
            attr_names if attr_names else None,
            values if values else None,
            None,
            skip,
        )

    if kwargs:
        for attr_name, value in kwargs.items():
            if attr_name not in self._attributes:
                raise ValueError(f"Unknown attribute: {attr_name}")
            setattr(self, attr_name, value)

        if condition is not None:
            cond_names: dict[str, str] = {}
            cond_values: dict[str, Any] = {}
            cond_expr = condition.serialize(cond_names, cond_values)
            attr_names = {v: k for k, v in cond_names.items()}
            return client, table, key, None, cond_expr, attr_names, cond_values, kwargs, skip

        return client, table, key, None, None, None, None, kwargs, skip

    return client, table, key, None, None, None, None, None, skip


def finalize_update(self: Model, skip: bool) -> None:
    """Finalize update operation - run after hooks."""
    if not skip:
        self._run_hooks(HookType.AFTER_UPDATE)


def prepare_update_by_key(
    cls: type[M], condition: Condition | None, kwargs: dict[str, Any]
) -> UpdateByKeyResult | None:
    """Prepare update_by_key. Returns tuple or None if nothing to update."""
    key, updates = cls._extract_key_from_kwargs(kwargs)

    if not updates:
        return None

    for attr_name in updates:
        if attr_name not in cls._attributes:
            raise ValueError(f"Unknown attribute: {attr_name}")

    client = cls._get_client()
    table = cls._get_table()

    if condition is not None:
        names: dict[str, str] = {}
        values: dict[str, Any] = {}
        cond_expr = condition.serialize(names, values)
        attr_names = {v: k for k, v in names.items()}
        # Rename value placeholders to avoid collision
        renamed_values: dict[str, Any] = {}
        renamed_expr = cond_expr
        for old_key, val in values.items():
            new_key = old_key.replace(":v", ":cond")
            renamed_values[new_key] = val
            renamed_expr = renamed_expr.replace(old_key, new_key)
        return (
            client,
            table,
            key,
            updates,
            renamed_expr,
            attr_names if attr_names else None,
            renamed_values if renamed_values else None,
        )

    return client, table, key, updates, None, None, None


def prepare_delete_by_key(
    cls: type[M], condition: Condition | None, kwargs: dict[str, Any]
) -> DeleteByKeyResult:
    """Prepare delete_by_key. Returns (client, table, key, cond_expr, attr_names, attr_values)."""
    key, _ = cls._extract_key_from_kwargs(kwargs)

    client = cls._get_client()
    table = cls._get_table()

    if condition is not None:
        names: dict[str, str] = {}
        values: dict[str, Any] = {}
        cond_expr = condition.serialize(names, values)
        attr_names = {v: k for k, v in names.items()}
        return client, table, key, cond_expr, attr_names, values

    return client, table, key, None, None, None
