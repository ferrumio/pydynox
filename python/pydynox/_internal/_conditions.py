"""Internal condition classes for building DynamoDB expressions.

These classes are not part of the public API. Users interact with them
through attribute operators like `User.age > 18`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pydynox.attributes import Attribute


class ConditionMixin:
    """Mixin that adds __and__, __or__, __invert__ to condition classes."""

    def __and__(self, other: Any) -> ConditionAnd:
        return ConditionAnd(self, other)

    def __or__(self, other: Any) -> ConditionOr:
        return ConditionOr(self, other)

    def __invert__(self) -> ConditionNot:
        return ConditionNot(self)


class ConditionPath:
    """Wraps an attribute for building conditions.

    Supports nested access via ["key"] and [index].
    Users never create this directly - it's created by Attribute operators.
    """

    def __init__(
        self,
        attribute: Attribute[Any] | None = None,
        path: list[str] | None = None,
        attr_type: str | None = None,
    ):
        self.attribute = attribute
        self.path = path or ([attribute.attr_name] if attribute and attribute.attr_name else [])
        self.attr_type = attr_type or (attribute.attr_type if attribute else None)

    def __getitem__(self, key: str | int) -> ConditionPath:
        """Access nested map key or list index."""
        new_path = self.path.copy()
        if isinstance(key, int):
            # List index: append [n] to last segment
            if new_path:
                new_path[-1] = f"{new_path[-1]}[{key}]"
            else:
                new_path.append(f"[{key}]")
        else:
            # Map key: add new segment
            new_path.append(key)
        return ConditionPath(path=new_path, attr_type=None)

    # Comparison operators
    def __eq__(self, other: Any) -> ConditionComparison:  # type: ignore[override]
        return ConditionComparison("=", self, other)

    def __ne__(self, other: Any) -> ConditionComparison:  # type: ignore[override]
        return ConditionComparison("<>", self, other)

    def __lt__(self, other: Any) -> ConditionComparison:
        return ConditionComparison("<", self, other)

    def __le__(self, other: Any) -> ConditionComparison:
        return ConditionComparison("<=", self, other)

    def __gt__(self, other: Any) -> ConditionComparison:
        return ConditionComparison(">", self, other)

    def __ge__(self, other: Any) -> ConditionComparison:
        return ConditionComparison(">=", self, other)

    # Function-style conditions
    def exists(self) -> ConditionExists:
        return ConditionExists(self)

    def not_exists(self) -> ConditionNotExists:
        return ConditionNotExists(self)

    def begins_with(self, prefix: str) -> ConditionBeginsWith:
        return ConditionBeginsWith(self, prefix)

    def contains(self, value: Any) -> ConditionContains:
        return ConditionContains(self, value)

    def between(self, lower: Any, upper: Any) -> ConditionBetween:
        return ConditionBetween(self, lower, upper)

    def is_in(self, *values: Any) -> ConditionIn:
        return ConditionIn(self, *values)

    def _serialize_path(self, names: dict[str, str]) -> str:
        """Serialize path with placeholder names."""
        parts = []
        for segment in self.path:
            # Handle list index notation
            if "[" in segment:
                base, rest = segment.split("[", 1)
                if base:
                    placeholder = self._get_name_placeholder(base, names)
                    parts.append(f"{placeholder}[{rest}")
                else:
                    parts.append(f"[{rest}")
            else:
                placeholder = self._get_name_placeholder(segment, names)
                parts.append(placeholder)
        return ".".join(parts)

    def _get_name_placeholder(self, name: str, names: dict[str, str]) -> str:
        """Get or create placeholder for attribute name."""
        if name not in names:
            names[name] = f"#n{len(names)}"
        return names[name]


class ConditionComparison(ConditionMixin):
    """Comparison condition (=, <>, <, <=, >, >=)."""

    def __init__(self, operator: str, path: ConditionPath, value: Any):
        self.operator = operator
        self.path = path
        self.value = value

    def serialize(self, names: dict[str, str], values: dict[str, Any]) -> str:
        path_str = self.path._serialize_path(names)
        value_placeholder = _get_value_placeholder(self.value, values)
        return f"{path_str} {self.operator} {value_placeholder}"


class ConditionBetween(ConditionMixin):
    """BETWEEN condition."""

    def __init__(self, path: ConditionPath, lower: Any, upper: Any):
        self.path = path
        self.lower = lower
        self.upper = upper

    def serialize(self, names: dict[str, str], values: dict[str, Any]) -> str:
        path_str = self.path._serialize_path(names)
        lower_ph = _get_value_placeholder(self.lower, values)
        upper_ph = _get_value_placeholder(self.upper, values)
        return f"{path_str} BETWEEN {lower_ph} AND {upper_ph}"


class ConditionIn(ConditionMixin):
    """IN condition."""

    def __init__(self, path: ConditionPath, *in_values: Any):
        self.path = path
        self.in_values = in_values

    def serialize(self, names: dict[str, str], values: dict[str, Any]) -> str:
        path_str = self.path._serialize_path(names)
        placeholders = [_get_value_placeholder(v, values) for v in self.in_values]
        return f"{path_str} IN ({', '.join(placeholders)})"


class ConditionExists(ConditionMixin):
    """attribute_exists() condition."""

    def __init__(self, path: ConditionPath):
        self.path = path

    def serialize(self, names: dict[str, str], values: dict[str, Any]) -> str:  # noqa: ARG002
        path_str = self.path._serialize_path(names)
        return f"attribute_exists({path_str})"


class ConditionNotExists(ConditionMixin):
    """attribute_not_exists() condition."""

    def __init__(self, path: ConditionPath):
        self.path = path

    def serialize(self, names: dict[str, str], values: dict[str, Any]) -> str:  # noqa: ARG002
        path_str = self.path._serialize_path(names)
        return f"attribute_not_exists({path_str})"


class ConditionBeginsWith(ConditionMixin):
    """begins_with() condition."""

    def __init__(self, path: ConditionPath, prefix: str):
        self.path = path
        self.prefix = prefix

    def serialize(self, names: dict[str, str], values: dict[str, Any]) -> str:
        path_str = self.path._serialize_path(names)
        prefix_ph = _get_value_placeholder(self.prefix, values)
        return f"begins_with({path_str}, {prefix_ph})"


class ConditionContains(ConditionMixin):
    """contains() condition."""

    def __init__(self, path: ConditionPath, value: Any):
        self.path = path
        self.value = value

    def serialize(self, names: dict[str, str], values: dict[str, Any]) -> str:
        path_str = self.path._serialize_path(names)
        value_ph = _get_value_placeholder(self.value, values)
        return f"contains({path_str}, {value_ph})"


class ConditionAnd(ConditionMixin):
    """AND condition."""

    def __init__(self, left: Any, right: Any):
        self.left = left
        self.right = right

    def serialize(self, names: dict[str, str], values: dict[str, Any]) -> str:
        left_str = self.left.serialize(names, values)
        right_str = self.right.serialize(names, values)
        return f"({left_str} AND {right_str})"


class ConditionOr(ConditionMixin):
    """OR condition."""

    def __init__(self, left: Any, right: Any):
        self.left = left
        self.right = right

    def serialize(self, names: dict[str, str], values: dict[str, Any]) -> str:
        left_str = self.left.serialize(names, values)
        right_str = self.right.serialize(names, values)
        return f"({left_str} OR {right_str})"


class ConditionNot(ConditionMixin):
    """NOT condition."""

    def __init__(self, condition: Any):
        self.condition = condition

    def serialize(self, names: dict[str, str], values: dict[str, Any]) -> str:
        cond_str = self.condition.serialize(names, values)
        return f"(NOT {cond_str})"


def _get_value_placeholder(value: Any, values: dict[str, Any]) -> str:
    """Get or create placeholder for a value."""
    placeholder = f":v{len(values)}"
    values[placeholder] = value
    return placeholder
