"""Batch operations for Model: batch_get (async default), sync_batch_get."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, TypeVar

from pydynox.hooks import HookType

if TYPE_CHECKING:
    from pydynox.model import Model

M = TypeVar("M", bound="Model")


def _dynamo_projection(cls: type[M], projection: list[str] | None) -> list[list[str]] | None:
    if not projection:
        return None
    return [cls._dynamo_path(path) for path in projection]


async def batch_get(
    cls: type[M],
    keys: list[dict[str, Any]],
    consistent_read: bool | None = None,
    as_dict: bool = False,
    projection: list[str] | None = None,
) -> list[M] | list[dict[str, Any]]:
    """Async batch get items by keys (default, no prefix).

    Args:
        keys: List of key dicts (each with partition_key and optional sort_key).
        consistent_read: If True, use strongly consistent read.
        as_dict: If True, return dicts instead of Model instances.
        projection: List of attribute names to fetch. Other fields get their
            default or None. Required fields must be included.

    Returns:
        List of model instances or dicts.
    """
    if not keys:
        return []

    client = cls._get_read_client()
    table = cls._get_table()

    # Translate python key names to DynamoDB aliases
    aliased_keys = [{cls._py_to_dynamo.get(k, k): v for k, v in key.items()} for key in keys]

    items = await client.batch_get(
        table,
        aliased_keys,
        consistent_read=consistent_read or False,
        _projection_paths=_dynamo_projection(cls, projection),
    )

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
    projection: list[str] | None = None,
) -> list[M] | list[dict[str, Any]]:
    """Sync batch get items by keys.

    Args:
        keys: List of key dicts (each with partition_key and optional sort_key).
        consistent_read: If True, use strongly consistent read.
        as_dict: If True, return dicts instead of Model instances.
        projection: List of attribute names to fetch. Other fields get their
            default or None. Required fields must be included.

    Returns:
        List of model instances or dicts.
    """
    if not keys:
        return []

    client = cls._get_read_client()
    table = cls._get_table()

    # Translate python key names to DynamoDB aliases
    aliased_keys = [{cls._py_to_dynamo.get(k, k): v for k, v in key.items()} for key in keys]

    items = client.sync_batch_get(
        table,
        aliased_keys,
        consistent_read=consistent_read or False,
        _projection_paths=_dynamo_projection(cls, projection),
    )

    if as_dict:
        return items

    # Convert to model instances
    instances = [cls.from_dict(item) for item in items]

    skip = cls.model_config.skip_hooks if hasattr(cls, "model_config") else False
    if not skip:
        for instance in instances:
            instance._run_hooks(HookType.AFTER_LOAD)

    return instances
