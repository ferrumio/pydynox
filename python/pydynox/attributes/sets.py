"""Set attribute types (StringSet, NumberSet)."""

from __future__ import annotations

from typing import Any

from pydynox.attributes.base import Attribute


class StringSetAttribute(Attribute[set[str]]):
    """DynamoDB native string set (SS).

    Stores a set of unique strings. DynamoDB sets don't allow duplicates
    and don't preserve order.

    Example:
        >>> from pydynox import Model, ModelConfig
        >>> from pydynox.attributes import StringAttribute, StringSetAttribute
        >>>
        >>> class User(Model):
        ...     model_config = ModelConfig(table="users")
        ...     pk = StringAttribute(partition_key=True)
        ...     tags = StringSetAttribute()
        >>>
        >>> user = User(pk="USER#1", tags={"admin", "verified"})
        >>> user.save()
    """

    attr_type = "SS"

    def serialize(self, value: set[str] | None) -> list[str] | None:
        """Convert set to list for DynamoDB.

        Args:
            value: Set of strings.

        Returns:
            List of strings or None.
        """
        if value is None or len(value) == 0:
            return None
        return list(value)

    def deserialize(self, value: Any) -> set[str]:
        """Convert list back to set.

        Args:
            value: List from DynamoDB.

        Returns:
            Set of strings.
        """
        if value is None:
            return set()
        return set(value)


class NumberSetAttribute(Attribute[set[int | float]]):
    """DynamoDB native number set (NS).

    Stores a set of unique numbers. DynamoDB sets don't allow duplicates
    and don't preserve order.

    Example:
        >>> from pydynox import Model, ModelConfig
        >>> from pydynox.attributes import StringAttribute, NumberSetAttribute
        >>>
        >>> class User(Model):
        ...     model_config = ModelConfig(table="users")
        ...     pk = StringAttribute(partition_key=True)
        ...     scores = NumberSetAttribute()
        >>>
        >>> user = User(pk="USER#1", scores={100, 95, 88})
        >>> user.save()
    """

    attr_type = "NS"

    def serialize(self, value: set[int | float] | None) -> list[str] | None:
        """Convert set to list of strings for DynamoDB.

        Args:
            value: Set of numbers.

        Returns:
            List of number strings or None.
        """
        if value is None or len(value) == 0:
            return None
        return [str(v) for v in value]

    def deserialize(self, value: Any) -> set[int | float]:
        """Convert list of strings back to set of numbers.

        Args:
            value: List of number strings from DynamoDB.

        Returns:
            Set of numbers.
        """
        if value is None:
            return set()
        result: set[int | float] = set()
        for v in value:
            num = float(v)
            # Return int if it's a whole number
            if num.is_integer():
                result.add(int(num))
            else:
                result.add(num)
        return result
