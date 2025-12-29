"""Attribute types for Model definitions."""

from typing import Any, Generic, Optional, TypeVar

T = TypeVar("T")


class Attribute(Generic[T]):
    """Base attribute class for Model fields.

    Attributes define the schema of a DynamoDB item. They can be marked
    as hash_key or range_key to define the table's primary key.

    Example:
        >>> class User(Model):
        ...     pk = StringAttribute(hash_key=True)
        ...     sk = StringAttribute(range_key=True)
        ...     name = StringAttribute()
        ...     age = NumberAttribute()
    """

    attr_type: str = "S"  # Default to string

    def __init__(
        self,
        hash_key: bool = False,
        range_key: bool = False,
        default: Optional[T] = None,
        null: bool = True,
    ):
        """Create an attribute.

        Args:
            hash_key: True if this is the partition key.
            range_key: True if this is the sort key.
            default: Default value when not provided.
            null: Whether None is allowed.
        """
        self.hash_key = hash_key
        self.range_key = range_key
        self.default = default
        self.null = null
        self.attr_name: Optional[str] = None

    def serialize(self, value: T) -> Any:
        """Convert Python value to DynamoDB format."""
        return value

    def deserialize(self, value: Any) -> T:
        """Convert DynamoDB value to Python format."""
        return value


class StringAttribute(Attribute[str]):
    """String attribute (DynamoDB type S)."""

    attr_type = "S"


class NumberAttribute(Attribute[float]):
    """Number attribute (DynamoDB type N).

    Stores both int and float values.
    """

    attr_type = "N"


class BooleanAttribute(Attribute[bool]):
    """Boolean attribute (DynamoDB type BOOL)."""

    attr_type = "BOOL"


class BinaryAttribute(Attribute[bytes]):
    """Binary attribute (DynamoDB type B)."""

    attr_type = "B"


class ListAttribute(Attribute[list]):
    """List attribute (DynamoDB type L)."""

    attr_type = "L"


class MapAttribute(Attribute[dict]):
    """Map attribute (DynamoDB type M)."""

    attr_type = "M"
