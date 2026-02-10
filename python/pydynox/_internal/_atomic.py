"""Internal atomic update classes for building DynamoDB update expressions."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pydynox.attributes import Attribute

__all__ = [
    "AtomicPath",
    "AtomicSet",
    "AtomicAdd",
    "AtomicRemove",
    "AtomicAppend",
    "AtomicPrepend",
    "AtomicIfNotExists",
    "AtomicOp",
    "serialize_atomic",
]


class AtomicPath:
    """Wraps an attribute for building atomic updates."""

    def __init__(
        self,
        attribute: Attribute[Any] | None = None,
        path: list[str] | None = None,
    ):
        self.attribute = attribute
        if path is not None:
            self.path = path
        elif attribute and attribute.attr_name:
            # Use alias for DynamoDB expression if set, otherwise python name
            dynamo_name = getattr(attribute, "alias", None) or attribute.attr_name
            self.path = [dynamo_name]
        else:
            self.path = []

    def _serialize_path(self, names: dict[str, str]) -> str:
        parts = []
        for segment in self.path:
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
        if name not in names:
            names[name] = f"#n{len(names)}"
        return names[name]


class AtomicSet:
    """SET field = value."""

    def __init__(self, path: AtomicPath, value: Any):
        self.path = path
        self.value = value

    def serialize(self, names: dict[str, str], values: dict[str, Any]) -> str:
        path_str = self.path._serialize_path(names)
        value_ph = _get_value_placeholder(self.value, values)
        return f"{path_str} = {value_ph}"


class AtomicAdd:
    """SET field = field + value."""

    def __init__(self, path: AtomicPath, value: int | float):
        self.path = path
        self.value = value

    def serialize(self, names: dict[str, str], values: dict[str, Any]) -> str:
        path_str = self.path._serialize_path(names)
        value_ph = _get_value_placeholder(self.value, values)
        return f"{path_str} = {path_str} + {value_ph}"


class AtomicRemove:
    """REMOVE field."""

    def __init__(self, path: AtomicPath):
        self.path = path

    def serialize(self, names: dict[str, str], values: dict[str, Any]) -> str:  # noqa: ARG002
        return self.path._serialize_path(names)


class AtomicAppend:
    """SET field = list_append(field, value)."""

    def __init__(self, path: AtomicPath, items: list[Any]):
        self.path = path
        self.items = items

    def serialize(self, names: dict[str, str], values: dict[str, Any]) -> str:
        path_str = self.path._serialize_path(names)
        value_ph = _get_value_placeholder(self.items, values)
        return f"{path_str} = list_append({path_str}, {value_ph})"


class AtomicPrepend:
    """SET field = list_append(value, field)."""

    def __init__(self, path: AtomicPath, items: list[Any]):
        self.path = path
        self.items = items

    def serialize(self, names: dict[str, str], values: dict[str, Any]) -> str:
        path_str = self.path._serialize_path(names)
        value_ph = _get_value_placeholder(self.items, values)
        return f"{path_str} = list_append({value_ph}, {path_str})"


class AtomicIfNotExists:
    """SET field = if_not_exists(field, value)."""

    def __init__(self, path: AtomicPath, value: Any):
        self.path = path
        self.value = value

    def serialize(self, names: dict[str, str], values: dict[str, Any]) -> str:
        path_str = self.path._serialize_path(names)
        value_ph = _get_value_placeholder(self.value, values)
        return f"{path_str} = if_not_exists({path_str}, {value_ph})"


def _get_value_placeholder(value: Any, values: dict[str, Any]) -> str:
    placeholder = f":v{len(values)}"
    values[placeholder] = value
    return placeholder


AtomicOp = AtomicSet | AtomicAdd | AtomicRemove | AtomicAppend | AtomicPrepend | AtomicIfNotExists


def serialize_atomic(ops: list[AtomicOp]) -> tuple[str, dict[str, str], dict[str, Any]]:
    """Serialize multiple atomic operations into a single expression."""
    names: dict[str, str] = {}
    values: dict[str, Any] = {}
    set_clauses: list[str] = []
    remove_clauses: list[str] = []

    for op in ops:
        if isinstance(op, AtomicRemove):
            remove_clauses.append(op.serialize(names, values))
        else:
            set_clauses.append(op.serialize(names, values))

    parts = []
    if set_clauses:
        parts.append(f"SET {', '.join(set_clauses)}")
    if remove_clauses:
        parts.append(f"REMOVE {', '.join(remove_clauses)}")

    return " ".join(parts), names, values
