"""Async CRUD operations (default): get, save, delete, update."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, TypeVar

from pydynox._internal._model._helpers import (
    finalize_delete,
    finalize_get,
    finalize_save,
    finalize_update,
    prepare_delete,
    prepare_delete_by_key,
    prepare_get,
    prepare_smart_save,
    prepare_update,
    prepare_update_by_key,
)
from pydynox._internal._operations_metrics import (
    _start_s3_metrics_collection,
    _stop_s3_metrics_collection,
)

if TYPE_CHECKING:
    from pydynox._internal._atomic import AtomicOp
    from pydynox.conditions import Condition
    from pydynox.model import Model

M = TypeVar("M", bound="Model")


async def get(
    cls: type[M], consistent_read: bool | None = None, as_dict: bool = False, **keys: Any
) -> M | dict[str, Any] | None:
    """Async get item by key (default). Returns model instance, dict, or None."""
    client, table, keys_dict, use_consistent = prepare_get(cls, consistent_read, keys)
    item = await client.get_item(table, keys_dict, consistent_read=use_consistent)

    if client._last_metrics is not None:
        cls._record_metrics(client._last_metrics, "get")

    if item is None:
        return None
    if as_dict:
        return item
    return finalize_get(cls, item)


async def save(
    self: Model,
    condition: Condition | None = None,
    skip_hooks: bool | None = None,
    full_replace: bool = False,
) -> None:
    """Async save model to DynamoDB (default). Uses smart update (only changed fields)."""
    _start_s3_metrics_collection()
    await self._upload_s3_files()
    s3_duration, s3_calls, s3_uploaded, s3_downloaded = _stop_s3_metrics_collection()

    (
        client,
        table,
        key_or_item,
        cond_expr,
        attr_names,
        attr_values,
        skip,
        use_update,
        updates,
    ) = prepare_smart_save(self, condition, skip_hooks, full_replace)

    if use_update and updates:
        # Smart update: UpdateItem with only changed fields
        if cond_expr is not None:
            await client.update_item(
                table,
                key_or_item,
                updates=updates,
                condition_expression=cond_expr,
                expression_attribute_names=attr_names,
                expression_attribute_values=attr_values,
            )
        else:
            await client.update_item(table, key_or_item, updates=updates)
    else:
        # Full replace: PutItem with all fields
        if cond_expr is not None:
            await client.put_item(
                table,
                key_or_item,
                condition_expression=cond_expr,
                expression_attribute_names=attr_names,
                expression_attribute_values=attr_values,
            )
        else:
            await client.put_item(table, key_or_item)

    if client._last_metrics is not None:
        op_type = "update" if use_update else "put"
        self.__class__._record_metrics(client._last_metrics, op_type)

    if s3_calls > 0:
        self.__class__._metrics_storage.total.add_s3(
            s3_duration, s3_calls, s3_uploaded, s3_downloaded
        )

    finalize_save(self, skip)


async def delete(
    self: Model, condition: Condition | None = None, skip_hooks: bool | None = None
) -> None:
    """Async delete model from DynamoDB (default)."""
    client, table, key, cond_expr, attr_names, attr_values, skip = prepare_delete(
        self, condition, skip_hooks
    )

    if cond_expr is not None:
        await client.delete_item(
            table,
            key,
            condition_expression=cond_expr,
            expression_attribute_names=attr_names,
            expression_attribute_values=attr_values,
        )
    else:
        await client.delete_item(table, key)

    if client._last_metrics is not None:
        self.__class__._record_metrics(client._last_metrics, "delete")

    _start_s3_metrics_collection()
    await self._delete_s3_files()
    s3_duration, s3_calls, s3_uploaded, s3_downloaded = _stop_s3_metrics_collection()

    if s3_calls > 0:
        self.__class__._metrics_storage.total.add_s3(
            s3_duration, s3_calls, s3_uploaded, s3_downloaded
        )

    finalize_delete(self, skip)


async def update(
    self: Model,
    atomic: list[AtomicOp] | None = None,
    condition: Condition | None = None,
    skip_hooks: bool | None = None,
    **kwargs: Any,
) -> None:
    """Async update specific attributes (default)."""
    client, table, key, update_expr, cond_expr, attr_names, attr_values, updates, skip = (
        prepare_update(self, atomic, condition, skip_hooks, kwargs)
    )

    if update_expr is not None:
        await client.update_item(
            table,
            key,
            update_expression=update_expr,
            condition_expression=cond_expr,
            expression_attribute_names=attr_names,
            expression_attribute_values=attr_values,
        )
    elif updates is not None:
        if cond_expr is not None:
            await client.update_item(
                table,
                key,
                updates=updates,
                condition_expression=cond_expr,
                expression_attribute_names=attr_names,
                expression_attribute_values=attr_values,
            )
        else:
            await client.update_item(table, key, updates=updates)

    if client._last_metrics is not None:
        self.__class__._record_metrics(client._last_metrics, "update")

    finalize_update(self, skip)


async def update_by_key(
    cls: type[M],
    condition: Condition | None = None,
    **kwargs: Any,
) -> None:
    """Async update item by key without fetching (default). No hooks."""
    result = prepare_update_by_key(cls, condition, kwargs)
    if result is None:
        return

    client, table, key, updates, cond_expr, attr_names, attr_values = result
    if cond_expr is not None:
        await client.update_item(
            table,
            key,
            updates=updates,
            condition_expression=cond_expr,
            expression_attribute_names=attr_names,
            expression_attribute_values=attr_values,
        )
    else:
        await client.update_item(table, key, updates=updates)

    if client._last_metrics is not None:
        cls._record_metrics(client._last_metrics, "update")


async def delete_by_key(
    cls: type[M],
    condition: Condition | None = None,
    **kwargs: Any,
) -> None:
    """Async delete item by key without fetching (default). No hooks."""
    client, table, key, cond_expr, attr_names, attr_values = prepare_delete_by_key(
        cls, condition, kwargs
    )

    if cond_expr is not None:
        await client.delete_item(
            table,
            key,
            condition_expression=cond_expr,
            expression_attribute_names=attr_names,
            expression_attribute_values=attr_values,
        )
    else:
        await client.delete_item(table, key)

    if client._last_metrics is not None:
        cls._record_metrics(client._last_metrics, "delete")
