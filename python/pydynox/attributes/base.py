"""Base Attribute class."""

from __future__ import annotations

from typing import Any, Generic, TypeVar, overload

from pydynox._internal._atomic import (
    AtomicAdd,
    AtomicAppend,
    AtomicIfNotExists,
    AtomicPath,
    AtomicPrepend,
    AtomicRemove,
    AtomicSet,
)
from pydynox._internal._conditions import (
    ConditionBeginsWith,
    ConditionBetween,
    ConditionComparison,
    ConditionContains,
    ConditionExists,
    ConditionIn,
    ConditionNotExists,
    ConditionPath,
)

T = TypeVar("T")
_A = TypeVar("_A", bound="Attribute[Any]")


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
        default: T | None = None,
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
        self.attr_name: str | None = None

    def __set__(self, instance: Any, value: T | None) -> None:
        """Set the attribute value on the model instance."""
        if instance is not None and self.attr_name is not None:
            instance.__dict__[self.attr_name] = value

    @overload
    def __get__(self: _A, instance: None, owner: type[Any]) -> _A: ...

    @overload
    def __get__(self, instance: Any, owner: type[Any]) -> T | None: ...

    def __get__(self: _A, instance: Any, owner: type[Any]) -> _A | T | None:
        """Get the attribute value from the model instance.

        When accessed on the class (User.pk), returns the Attribute itself.
        When accessed on an instance (user.pk), returns the actual value.
        """
        if instance is None:
            # Accessed on class, return the attribute for conditions
            return self
        # Accessed on instance, return the value
        if self.attr_name is not None:
            return instance.__dict__.get(self.attr_name)
        return None

    def serialize(self, value: T | None) -> Any:
        """Convert Python value to DynamoDB format."""
        return value

    def deserialize(self, value: Any) -> T | None:
        """Convert DynamoDB value to Python format."""
        return value  # type: ignore[no-any-return]

    # Condition operators
    def _get_path(self) -> ConditionPath:
        """Get ConditionPath for this attribute."""
        return ConditionPath(attribute=self)

    def __eq__(self, other: Any) -> ConditionComparison:  # type: ignore[override]
        return ConditionComparison("=", self._get_path(), other)

    def __ne__(self, other: Any) -> ConditionComparison:  # type: ignore[override]
        return ConditionComparison("<>", self._get_path(), other)

    def __lt__(self, other: Any) -> ConditionComparison:
        return ConditionComparison("<", self._get_path(), other)

    def __le__(self, other: Any) -> ConditionComparison:
        return ConditionComparison("<=", self._get_path(), other)

    def __gt__(self, other: Any) -> ConditionComparison:
        return ConditionComparison(">", self._get_path(), other)

    def __ge__(self, other: Any) -> ConditionComparison:
        return ConditionComparison(">=", self._get_path(), other)

    def __getitem__(self, key: str | int) -> ConditionPath:
        """Access nested map key or list index for conditions."""
        return self._get_path()[key]

    def exists(self) -> ConditionExists:
        """Check if attribute exists."""
        return self._get_path().exists()

    def not_exists(self) -> ConditionNotExists:
        """Check if attribute does not exist."""
        return self._get_path().not_exists()

    def begins_with(self, prefix: str) -> ConditionBeginsWith:
        """Check if string attribute starts with prefix."""
        return self._get_path().begins_with(prefix)

    def contains(self, value: Any) -> ConditionContains:
        """Check if list/set contains value or string contains substring."""
        return self._get_path().contains(value)

    def between(self, lower: Any, upper: Any) -> ConditionBetween:
        """Check if value is between lower and upper (inclusive)."""
        return self._get_path().between(lower, upper)

    def is_in(self, *values: Any) -> ConditionIn:
        """Check if value is in the given list."""
        return self._get_path().is_in(*values)

    # Atomic update methods
    def _get_atomic_path(self) -> AtomicPath:
        """Get AtomicPath for this attribute."""
        return AtomicPath(attribute=self)

    def set(self, value: Any) -> AtomicSet:
        """Set attribute to a value."""
        return AtomicSet(self._get_atomic_path(), value)

    def add(self, value: int | float) -> AtomicAdd:
        """Add to a number attribute (atomic increment/decrement)."""
        return AtomicAdd(self._get_atomic_path(), value)

    def remove(self) -> AtomicRemove:
        """Remove this attribute from the item."""
        return AtomicRemove(self._get_atomic_path())

    def append(self, items: list[Any]) -> AtomicAppend:
        """Append items to a list attribute."""
        return AtomicAppend(self._get_atomic_path(), items)

    def prepend(self, items: list[Any]) -> AtomicPrepend:
        """Prepend items to a list attribute."""
        return AtomicPrepend(self._get_atomic_path(), items)

    def if_not_exists(self, value: Any) -> AtomicIfNotExists:
        """Set attribute only if it doesn't exist."""
        return AtomicIfNotExists(self._get_atomic_path(), value)
