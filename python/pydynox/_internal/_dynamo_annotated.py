"""Synthesize ``Attribute`` instances from ``Annotated`` + :mod:`pydynox.dynamo` markers."""

from __future__ import annotations

import sys
from typing import Annotated, Any, get_args, get_origin

from pydynox.attributes import Attribute
from pydynox.attributes.primitives import (
    BinaryAttribute,
    BooleanAttribute,
    NumberAttribute,
    StringAttribute,
)
from pydynox.dynamo import (
    DynamoBinary,
    DynamoBoolean,
    DynamoFieldMarker,
    DynamoNumber,
    DynamoString,
)


def attribute_from_annotated(field_name: str, hint: Any) -> Attribute[Any] | None:
    """If *hint* is ``Annotated[T, Dynamo.*...]`, build the matching :class:`Attribute`."""
    origin = get_origin(hint)
    if origin is not Annotated:
        return None
    args = get_args(hint)
    if len(args) < 2:
        return None
    base, *metas = args
    marker: DynamoFieldMarker | None = None
    for m in metas:
        if isinstance(
            m,
            (DynamoString, DynamoNumber, DynamoBoolean, DynamoBinary),
        ):
            if marker is not None:
                raise TypeError(
                    f"{field_name!r}: at most one Dynamo.* marker is allowed in Annotated[...]."
                )
            marker = m
    if marker is None:
        return None

    if isinstance(marker, DynamoString):
        if base is not str:
            raise TypeError(
                f"{field_name!r}: Dynamo.String needs str, not {base!r}."
            )
        return StringAttribute(
            partition_key=marker.partition_key,
            sort_key=marker.sort_key,
            default=marker.default,
            required=marker.required,
            template=marker.template,
            discriminator=marker.discriminator,
            alias=marker.alias,
        )
    if isinstance(marker, DynamoNumber):
        if base not in (int, float):
            raise TypeError(
                f"{field_name!r}: Dynamo.Number requires int or float, not {base!r}."
            )
        return NumberAttribute(
            partition_key=marker.partition_key,
            sort_key=marker.sort_key,
            default=marker.default,
            required=marker.required,
            discriminator=marker.discriminator,
            alias=marker.alias,
        )
    if isinstance(marker, DynamoBoolean):
        if base is not bool:
            raise TypeError(
                f"{field_name!r}: Dynamo.Boolean requires bool, not {base!r}."
            )
        return BooleanAttribute(
            partition_key=marker.partition_key,
            sort_key=marker.sort_key,
            default=marker.default,
            required=marker.required,
            discriminator=marker.discriminator,
            alias=marker.alias,
        )
    if isinstance(marker, DynamoBinary):
        if base is not bytes:
            raise TypeError(
                f"{field_name!r}: Dynamo.Binary requires bytes, not {base!r}."
            )
        return BinaryAttribute(
            partition_key=marker.partition_key,
            sort_key=marker.sort_key,
            default=marker.default,
            required=marker.required,
            discriminator=marker.discriminator,
            alias=marker.alias,
        )
    return None


def _resolve_own_field_hints(cls: type) -> dict[str, Any] | None:
    """Resolve *cls*'s own ``__annotations__`` only (no MRO, no base-class hints).

    ``get_type_hints(cls)`` is unsuitable: it also evaluates all inherited
    annotations (including from :class:`pydynox.model.Model` with forward
    references), which can :exc:`NameError` before we even see a field to build.

    We must only evaluate the annotations declared in this class body.
    """
    own = cls.__dict__.get("__annotations__", {})
    if not own:
        return {}
    mod = sys.modules.get(cls.__module__)
    if mod is not None:
        cell: dict[str, Any] = dict(mod.__dict__)
    else:
        cell = {}
    # Allow self- and class-scoped forward references in hints.
    cell[cls.__name__] = cls
    cell[cls.__qualname__.split(".")[-1]] = cls
    for key, value in cls.__dict__.items():
        if not key.startswith("__"):
            cell.setdefault(key, value)
    out: dict[str, Any] = {}
    for fname, ann in own.items():
        if isinstance(ann, str):
            try:
                out[fname] = eval(  # noqa: S307 - same as typing.get_type_hints
                    ann, cell, cell
                )
            except (NameError, TypeError, SyntaxError, ValueError, AttributeError):
                return None
        else:
            out[fname] = ann
    return out


def apply_annotated_dynamo_fields(
    cls: type,
    namespace: dict[str, Any],
    attributes: dict[str, Attribute[Any]],
    partition_key: str | None,
    sort_key: str | None,
    discriminator_attr: str | None,
) -> tuple[str | None, str | None, str | None]:
    """Set descriptors from ``Annotated[..., Dynamo.*]`` on *cls* and merge *attributes*.

    Explicit ``X = StringAttribute(...)`` in the class body wins: do not
    replace if *fname* is already in *attributes* (including from bases).
    If *namespace[fname]* is already a descriptor, skip (descriptor wins).

    Returns updated (*partition_key*, *sort_key*, *discriminator_attr*).
    """
    own_ann = namespace.get("__annotations__", {})
    if not own_ann:
        return partition_key, sort_key, discriminator_attr
    hints = _resolve_own_field_hints(cls)
    if hints is None:
        return partition_key, sort_key, discriminator_attr
    for fname in own_ann:
        if isinstance(namespace.get(fname), Attribute):
            continue
        if fname in attributes:
            continue
        hint = hints.get(fname)
        if hint is None:
            continue
        built = attribute_from_annotated(fname, hint)
        if built is None:
            continue
        if built.partition_key:
            if partition_key is not None:
                raise ValueError(
                    f"Model {cls.__name__!r} has more than one partition key: "
                    f"{partition_key!r} and {fname!r}."
                )
            partition_key = fname
        if built.sort_key:
            if sort_key is not None:
                raise ValueError(
                    f"Model {cls.__name__!r} has more than one sort key: "
                    f"{sort_key!r} and {fname!r}."
                )
            sort_key = fname
        if getattr(built, "discriminator", False):
            if discriminator_attr is not None and discriminator_attr != fname:
                raise ValueError(
                    f"Model {cls.__name__!r} has more than one discriminator field: "
                    f"{discriminator_attr!r} and {fname!r}."
                )
            discriminator_attr = fname
        built.attr_name = fname
        attributes[fname] = built
        setattr(cls, fname, built)
    return partition_key, sort_key, discriminator_attr
