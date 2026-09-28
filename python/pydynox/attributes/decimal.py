"""Exact decimal attributes."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from pydynox import pydynox_core
from pydynox._internal._atomic import AtomicAdd, AtomicIfNotExists, AtomicSet
from pydynox.attributes.base import Attribute


class DecimalAttribute(Attribute[Decimal]):
    """Store exact decimal values as DynamoDB numbers.

    Accepts Decimal and integer values. Build fractional values from strings,
    such as Decimal("19.99"), to avoid binary floating-point rounding.

    Model reads return Decimal directly from the DynamoDB number text.
    NumberAttribute keeps its existing int/float behavior.
    """

    attr_type = "N"

    def __init__(
        self,
        partition_key: bool = False,
        sort_key: bool = False,
        default: Decimal | int | None = None,
        required: bool = False,
        discriminator: bool = False,
        alias: str | None = None,
    ):
        super().__init__(
            partition_key=partition_key,
            sort_key=sort_key,
            default=pydynox_core.validate_decimal(default),
            required=required,
            discriminator=discriminator,
            alias=alias,
        )

    def __set__(self, instance: Any, value: Decimal | int | None) -> None:
        super().__set__(instance, pydynox_core.validate_decimal(value))

    def serialize(self, value: Decimal | int | None) -> Decimal | None:
        """Validate an exact value before sending it to DynamoDB."""
        return pydynox_core.validate_decimal(value)

    def deserialize(self, value: Any) -> Decimal | None:
        """Accept an exact decoded value, rejecting already rounded floats."""
        return pydynox_core.validate_decimal(value)

    def set(self, value: Any) -> AtomicSet:
        """Set an exact value through an update expression."""
        return AtomicSet(self._get_atomic_path(), self.serialize(value))

    def if_not_exists(self, value: Any) -> AtomicIfNotExists:
        """Set an exact default when the attribute is missing."""
        return AtomicIfNotExists(self._get_atomic_path(), self.serialize(value))

    def add(self, value: Any) -> AtomicAdd:
        """Atomically add an exact decimal value."""
        return AtomicAdd(self._get_atomic_path(), pydynox_core.validate_decimal(value))
