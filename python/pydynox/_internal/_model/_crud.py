"""Sync CRUD operations: get, save, delete, update."""

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

if TYPE_CHECKING:
    from pydynox._internal._atomic import AtomicOp
    from pydynox.conditions import Condition
    from pydynox.model import Model

M = TypeVar("M", bound="Model")


def get(
    cls: type[M], consistent_read: bool | None = None, as_dict: bool = False, **keys: Any
) -> M | dict[str, Any] | None:
    """Get an item by key. Returns model instance, dict, or None."""
    # prepare: get client, table, resolve consistent_read
    client, table, keys_dict, use_consistent = prepare_get(cls, consistent_read, keys)
    item = client.get_item(table, keys_dict, consistent_read=use_consistent)

    # Record metrics from client
    if client._last_metrics is not None:
        cls._record_metrics(client._last_metrics, "get")

    if item is None:
        return None
    if as_dict:
        return item
    # finalize: convert to model, run AFTER_LOAD hooks
    return finalize_get(cls, item)


def save(self: Model, condition: Condition | None = None, skip_hooks: bool | None = None) -> None:
    """Save model to DynamoDB."""
    # S3 upload before prepare (needs to happen before to_dict)
    self._upload_s3_files()
    # prepare: run BEFORE_SAVE hooks, auto-generate, version condition, size check
    client, table, item, cond_expr, attr_names, attr_values, skip = prepare_save(
        self, condition, skip_hooks
    )

    if cond_expr is not None:
        client.put_item(
            table,
            item,
            condition_expression=cond_expr,
            expression_attribute_names=attr_names,
            expression_attribute_values=attr_values,
        )
    else:
        client.put_item(table, item)

    # Record metrics from client
    if client._last_metrics is not None:
        self.__class__._record_metrics(client._last_metrics, "put")

    # finalize: run AFTER_SAVE hooks
    finalize_save(self, skip)


def delete(self: Model, condition: Condition | None = None, skip_hooks: bool | None = None) -> None:
    """Delete model from DynamoDB."""
    # prepare: run BEFORE_DELETE hooks, version condition
    client, table, key, cond_expr, attr_names, attr_values, skip = prepare_delete(
        self, condition, skip_hooks
    )

    if cond_expr is not None:
        client.delete_item(
            table,
            key,
            condition_expression=cond_expr,
            expression_attribute_names=attr_names,
            expression_attribute_values=attr_values,
        )
    else:
        client.delete_item(table, key)

    # Record metrics from client
    if client._last_metrics is not None:
        self.__class__._record_metrics(client._last_metrics, "delete")

    # S3 cleanup after successful delete
    self._delete_s3_files()
    # finalize: run AFTER_DELETE hooks
    finalize_delete(self, skip)


def update(
    self: Model,
    atomic: list[AtomicOp] | None = None,
    condition: Condition | None = None,
    skip_hooks: bool | None = None,
    **kwargs: Any,
) -> None:
    """Update specific attributes."""
    # prepare: run BEFORE_UPDATE hooks, build expressions
    client, table, key, update_expr, cond_expr, attr_names, attr_values, updates, skip = (
        prepare_update(self, atomic, condition, skip_hooks, kwargs)
    )

    if update_expr is not None:
        client.update_item(
            table,
            key,
            update_expression=update_expr,
            condition_expression=cond_expr,
            expression_attribute_names=attr_names,
            expression_attribute_values=attr_values,
        )
    elif updates is not None:
        if cond_expr is not None:
            client.update_item(
                table,
                key,
                updates=updates,
                condition_expression=cond_expr,
                expression_attribute_names=attr_names,
                expression_attribute_values=attr_values,
            )
        else:
            client.update_item(table, key, updates=updates)

    # Record metrics from client
    if client._last_metrics is not None:
        self.__class__._record_metrics(client._last_metrics, "update")

    # finalize: run AFTER_UPDATE hooks
    finalize_update(self, skip)


def update_by_key(
    cls: type[M],
    condition: Condition | None = None,
    **kwargs: Any,
) -> None:
    """Update item by key without fetching. No hooks."""
    # prepare: extract key, validate attrs, build condition
    result = prepare_update_by_key(cls, condition, kwargs)
    if result is None:
        return

    client, table, key, updates, cond_expr, attr_names, attr_values = result
    if cond_expr is not None:
        client.update_item(
            table,
            key,
            updates=updates,
            condition_expression=cond_expr,
            expression_attribute_names=attr_names,
            expression_attribute_values=attr_values,
        )
    else:
        client.update_item(table, key, updates=updates)

    # Record metrics from client
    if client._last_metrics is not None:
        cls._record_metrics(client._last_metrics, "update")


def delete_by_key(
    cls: type[M],
    condition: Condition | None = None,
    **kwargs: Any,
) -> None:
    """Delete item by key without fetching. No hooks."""
    # prepare: extract key, build condition
    client, table, key, cond_expr, attr_names, attr_values = prepare_delete_by_key(
        cls, condition, kwargs
    )

    if cond_expr is not None:
        client.delete_item(
            table,
            key,
            condition_expression=cond_expr,
            expression_attribute_names=attr_names,
            expression_attribute_values=attr_values,
        )
    else:
        client.delete_item(table, key)

    # Record metrics from client
    if client._last_metrics is not None:
        cls._record_metrics(client._last_metrics, "delete")
