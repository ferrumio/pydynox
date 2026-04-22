"""`Annotated[... , Dynamo.*]` metadata for :class:`pydynox.Model` fields.

Use with :class:`typing.Annotated` to declare DynamoDB field semantics while
keeping a plain type for type checkers (``str``, ``int``, ...). Synthesized
``Attribute`` s match class-body ``StringAttribute`` / ``NumberAttribute`` /
etc. (legacy descriptor style is unchanged and takes precedence).

Example:

    from typing import Annotated, ClassVar

    from pydynox import Model, DynamoConfig, Dynamo
    from pydynox.attributes import StringAttribute

    class User(Model):
        dynamodb_config: ClassVar[DynamoConfig] = DynamoConfig(table="users")

        pk: Annotated[str, Dynamo.String(partition_key=True)]
        name: Annotated[str, Dynamo.String()]

    class LegacyUser(Model):
        dynamodb_config: ClassVar[DynamoConfig] = DynamoConfig(table="users")
        pk = StringAttribute(partition_key=True)
        name = StringAttribute()
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

__all__ = [
    "Dynamo",
    "DynamoString",
    "DynamoNumber",
    "DynamoBoolean",
    "DynamoBinary",
    "DynamoFieldMarker",
]


@dataclass(frozen=True, slots=True)
class DynamoString:
    """Metadata for a string field (maps to :class:`pydynox.attributes.StringAttribute`)."""

    partition_key: bool = False
    sort_key: bool = False
    default: str | None = None
    required: bool = False
    template: Any | None = None
    discriminator: bool = False
    alias: str | None = None


@dataclass(frozen=True, slots=True)
class DynamoNumber:
    """Metadata for a numeric field (maps to :class:`pydynox.attributes.NumberAttribute`)."""

    partition_key: bool = False
    sort_key: bool = False
    default: int | float | None = None
    required: bool = False
    discriminator: bool = False
    alias: str | None = None


@dataclass(frozen=True, slots=True)
class DynamoBoolean:
    """Metadata for a bool field (maps to :class:`pydynox.attributes.BooleanAttribute`)."""

    partition_key: bool = False
    sort_key: bool = False
    default: bool | None = None
    required: bool = False
    discriminator: bool = False
    alias: str | None = None


@dataclass(frozen=True, slots=True)
class DynamoBinary:
    """Metadata for a binary field (maps to :class:`pydynox.attributes.BinaryAttribute`)."""

    partition_key: bool = False
    sort_key: bool = False
    default: bytes | None = None
    required: bool = False
    discriminator: bool = False
    alias: str | None = None


DynamoFieldMarker = DynamoString | DynamoNumber | DynamoBoolean | DynamoBinary


class _DynamoNS:
    """Namespace for `Annotated` markers (e.g. ``Dynamo.String(...)``)."""

    String = DynamoString
    Number = DynamoNumber
    Boolean = DynamoBoolean
    Binary = DynamoBinary


Dynamo = _DynamoNS()
