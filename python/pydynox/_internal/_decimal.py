"""Internal numeric schemas for model reads."""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING, Any, NotRequired, TypedDict

if TYPE_CHECKING:
    from pydynox._internal._model._base import ModelBase


class NumberSchema(TypedDict):
    fields: frozenset[str]
    variants: dict[str, dict[str, frozenset[str]]]
    fallback_fields: NotRequired[frozenset[str]]


def model_read_client(client: Any, models: Sequence[type[ModelBase]]) -> Any:
    """Bind a schema to this read without changing the shared client."""
    fields = frozenset().union(*(model._decimal_fields for model in models))
    if not fields:
        return client

    variants: dict[str, dict[str, frozenset[str]]] = {}
    for model in models:
        candidates = {model, *model._discriminator_registry.values()}
        for candidate in candidates:
            if not issubclass(candidate, model) or not candidate._discriminator_attr:
                continue
            discriminator = candidate._py_to_dynamo.get(
                candidate._discriminator_attr, candidate._discriminator_attr
            )
            variants.setdefault(discriminator, {})[candidate.__name__] = (
                candidate._declared_decimal_fields
            )
    fallback_fields = frozenset().union(*(model._declared_decimal_fields for model in models))
    return client._for_model_read(
        NumberSchema(fields=fields, variants=variants, fallback_fields=fallback_fields)
    )
