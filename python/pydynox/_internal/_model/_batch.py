"""Batch operations for Model: batch_get (async default), sync_batch_get."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, TypeVar

from pydynox.hooks import HookType

if TYPE_CHECKING:
    from pydynox.model import Model

M = TypeVar("M", bound="Model")


async def batch_get(
    cls: type[M],
    keys: list[dict[str, Any]],
    consistent_read: bool | None = None,
    as_dict: bool = False,
) -> list[M] | list[dict[str, Any]]:
    """Async batch get items by keys (default, no prefix).

    Args:
        keys: List of key dicts (each with hash_key and optional range_key).
        consistent_read: If True, use strongly consistent read.
        as_dict: If True, return dicts instead of Model instances.

    Returns:
        List of model instances or dicts.
    """
    if not keys:
        return []

    client = cls._get_client()
    table = cls._get_table()

    # consistent_read is not yet supported by client.batch_get
    # but we keep the parameter for future compatibility
    _ = consistent_read

    # Call client async batch_get
    items = await client.batch_get(table, keys)

    if as_dict:
        return items

    # Convert to model instances
    instances = [cls.from_dict(item) for item in items]

    skip = cls.model_config.skip_hooks if hasattr(cls, "model_config") else False
    if not skip:
        for instance in instances:
            instance._run_hooks(HookType.AFTER_LOAD)

    return instances


def sync_batch_get(
    cls: type[M],
    keys: list[dict[str, Any]],
    consistent_read: bool | None = None,
    as_dict: bool = False,
) -> list[M] | list[dict[str, Any]]:
    """Sync batch get items by keys.

    Args:
        keys: List of key dicts (each with hash_key and optional range_key).
        consistent_read: If True, use strongly consistent read.
        as_dict: If True, return dicts instead of Model instances.

    Returns:
        List of model instances or dicts.
    """
    if not keys:
        return []

    client = cls._get_client()
    table = cls._get_table()

    # consistent_read is not yet supported by client.sync_batch_get
    # but we keep the parameter for future compatibility
    _ = consistent_read

    # Call client sync_batch_get
    items = client.sync_batch_get(table, keys)

    if as_dict:
        return items

    # Convert to model instances
    instances = [cls.from_dict(item) for item in items]

    skip = cls.model_config.skip_hooks if hasattr(cls, "model_config") else False
    if not skip:
        for instance in instances:
            instance._run_hooks(HookType.AFTER_LOAD)

    return instances
