"""Async CRUD operations: async_get, async_save, async_delete, async_update."""

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
    prepare_save,
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


async def async_get(
    cls: type[M], consistent_read: bool | None = None, as_dict: bool = False, **keys: Any
) -> M | dict[str, Any] | None:
    """Async get item by key. Returns model instance, dict, or None."""
    # prepare: get client, table, resolve consistent_read
    client, table, keys_dict, use_consistent = prepare_get(cls, consistent_read, keys)
    item = await client.async_get_item(table, keys_dict, consistent_read=use_consistent)

    # Record metrics from client
    if client._last_metrics is not None:
        cls._record_metrics(client._last_metrics, "get")

    if item is None:
        return None
    if as_dict:
        return item
    # finalize: convert to model, run AFTER_LOAD hooks
    return finalize_get(cls, item)


async def async_save(
    self: Model, condition: Condition | None = None, skip_hooks: bool | None = None
) -> None:
    """Async save model to DynamoDB."""
    # Start S3 metrics collection for uploads
    _start_s3_metrics_collection()

    # S3 upload before prepare (needs to happen before to_dict)
    await self._async_upload_s3_files()

    # Collect S3 metrics from uploads
    s3_duration, s3_calls, s3_uploaded, s3_downloaded = _stop_s3_metrics_collection()

    # prepare: run BEFORE_SAVE hooks, auto-generate, version condition, size check
    client, table, item, cond_expr, attr_names, attr_values, skip = prepare_save(
        self, condition, skip_hooks
    )

    if cond_expr is not None:
        await client.async_put_item(
            table,
            item,
            condition_expression=cond_expr,
            expression_attribute_names=attr_names,
            expression_attribute_values=attr_values,
        )
    else:
        await client.async_put_item(table, item)

    # Record metrics from client
    if client._last_metrics is not None:
        self.__class__._record_metrics(client._last_metrics, "put")

    # Record S3 metrics
    if s3_calls > 0:
        self.__class__._metrics_storage.total.add_s3(
            s3_duration, s3_calls, s3_uploaded, s3_downloaded
        )

    # finalize: run AFTER_SAVE hooks
    finalize_save(self, skip)


async def async_delete(
    self: Model, condition: Condition | None = None, skip_hooks: bool | None = None
) -> None:
    """Async delete model from DynamoDB."""
    # prepare: run BEFORE_DELETE hooks, version condition
    client, table, key, cond_expr, attr_names, attr_values, skip = prepare_delete(
        self, condition, skip_hooks
    )

    if cond_expr is not None:
        await client.async_delete_item(
            table,
            key,
            condition_expression=cond_expr,
            expression_attribute_names=attr_names,
            expression_attribute_values=attr_values,
        )
    else:
        await client.async_delete_item(table, key)

    # Record metrics from client
    if client._last_metrics is not None:
        self.__class__._record_metrics(client._last_metrics, "delete")

    # Start S3 metrics collection for deletes
    _start_s3_metrics_collection()

    # S3 cleanup after successful delete
    await self._async_delete_s3_files()

    # Collect S3 metrics from deletes
    s3_duration, s3_calls, s3_uploaded, s3_downloaded = _stop_s3_metrics_collection()

    # Record S3 metrics
    if s3_calls > 0:
        self.__class__._metrics_storage.total.add_s3(
            s3_duration, s3_calls, s3_uploaded, s3_downloaded
        )

    # finalize: run AFTER_DELETE hooks
    finalize_delete(self, skip)


async def async_update(
    self: Model,
    atomic: list[AtomicOp] | None = None,
    condition: Condition | None = None,
    skip_hooks: bool | None = None,
    **kwargs: Any,
) -> None:
    """Async update specific attributes."""
    # prepare: run BEFORE_UPDATE hooks, build expressions
    client, table, key, update_expr, cond_expr, attr_names, attr_values, updates, skip = (
        prepare_update(self, atomic, condition, skip_hooks, kwargs)
    )

    if update_expr is not None:
        await client.async_update_item(
            table,
            key,
            update_expression=update_expr,
            condition_expression=cond_expr,
            expression_attribute_names=attr_names,
            expression_attribute_values=attr_values,
        )
    elif updates is not None:
        if cond_expr is not None:
            await client.async_update_item(
                table,
                key,
                updates=updates,
                condition_expression=cond_expr,
                expression_attribute_names=attr_names,
                expression_attribute_values=attr_values,
            )
        else:
            await client.async_update_item(table, key, updates=updates)

    # Record metrics from client
    if client._last_metrics is not None:
        self.__class__._record_metrics(client._last_metrics, "update")

    # finalize: run AFTER_UPDATE hooks
    finalize_update(self, skip)


async def async_update_by_key(
    cls: type[M],
    condition: Condition | None = None,
    **kwargs: Any,
) -> None:
    """Async update item by key without fetching. No hooks."""
    # prepare: extract key, validate attrs, build condition
    result = prepare_update_by_key(cls, condition, kwargs)
    if result is None:
        return

    client, table, key, updates, cond_expr, attr_names, attr_values = result
    if cond_expr is not None:
        await client.async_update_item(
            table,
            key,
            updates=updates,
            condition_expression=cond_expr,
            expression_attribute_names=attr_names,
            expression_attribute_values=attr_values,
        )
    else:
        await client.async_update_item(table, key, updates=updates)

    # Record metrics from client
    if client._last_metrics is not None:
        cls._record_metrics(client._last_metrics, "update")


async def async_delete_by_key(
    cls: type[M],
    condition: Condition | None = None,
    **kwargs: Any,
) -> None:
    """Async delete item by key without fetching. No hooks."""
    # prepare: extract key, build condition
    client, table, key, cond_expr, attr_names, attr_values = prepare_delete_by_key(
        cls, condition, kwargs
    )

    if cond_expr is not None:
        await client.async_delete_item(
            table,
            key,
            condition_expression=cond_expr,
            expression_attribute_names=attr_names,
            expression_attribute_values=attr_values,
        )
    else:
        await client.async_delete_item(table, key)

    # Record metrics from client
    if client._last_metrics is not None:
        cls._record_metrics(client._last_metrics, "delete")
