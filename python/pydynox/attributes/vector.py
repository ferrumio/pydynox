"""Vector attribute support."""

from __future__ import annotations

import math
import struct
from collections.abc import Sequence
from typing import Any

from pydynox.attributes.base import Attribute


class VectorAttribute(Attribute[list[float]]):
    """A fixed-size vector stored as a DynamoDB list of numbers."""

    attr_type = "L"

    def __init__(
        self,
        dimensions: int,
        *,
        default: list[float] | None = None,
        required: bool = False,
        alias: str | None = None,
    ) -> None:
        if isinstance(dimensions, bool) or not isinstance(dimensions, int):
            raise TypeError("dimensions must be an integer")
        if not 1 <= dimensions <= 4096:
            raise ValueError("dimensions must be between 1 and 4096")

        super().__init__(
            default=default,
            required=required,
            alias=alias,
        )
        self.dimensions = dimensions

    def __set__(self, instance: Any, value: Any) -> None:
        if value is not None:
            value = self._validate(value)
        super().__set__(instance, value)

    def serialize(self, value: Any) -> list[float] | None:
        if value is None:
            return None
        return self._validate(value)

    def deserialize(self, value: Any) -> list[float] | None:
        if value is None:
            return None
        return self._validate(value)

    def _validate(self, value: Any) -> list[float]:
        if hasattr(value, "tolist"):
            value = value.tolist()

        if isinstance(value, (str, bytes, bytearray)) or not isinstance(value, Sequence):
            name = self.attr_name or "<unbound>"
            raise TypeError(f"VectorAttribute '{name}' requires a one-dimensional sequence")

        if len(value) != self.dimensions:
            name = self.attr_name or "<unbound>"
            raise ValueError(
                f"VectorAttribute '{name}' requires {self.dimensions} dimensions, got {len(value)}"
            )

        result: list[float] = []
        for index, item in enumerate(value):
            if isinstance(item, bool) or not isinstance(item, (int, float)):
                name = self.attr_name or "<unbound>"
                raise TypeError(
                    f"VectorAttribute '{name}' requires numeric values, "
                    f"got {type(item).__name__} at index {index}"
                )

            number = float(item)
            if not math.isfinite(number):
                name = self.attr_name or "<unbound>"
                raise ValueError(
                    f"VectorAttribute '{name}' contains a non-finite value at index {index}"
                )

            try:
                number = struct.unpack("!f", struct.pack("!f", number))[0]
            except OverflowError as exc:
                name = self.attr_name or "<unbound>"
                raise ValueError(
                    f"VectorAttribute '{name}' contains a value outside float32 range "
                    f"at index {index}"
                ) from exc
            result.append(number)

        return result
