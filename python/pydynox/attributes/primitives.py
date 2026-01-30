"""Primitive attribute types (String, Number, Boolean, Binary, List, Map)."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from pydynox.attributes.base import Attribute


@dataclass
class _TemplatePart:
    """Part of a parsed template."""

    is_placeholder: bool
    value: str  # literal text or attribute name


def _parse_template(template: str) -> list[_TemplatePart]:
    """Parse template like 'USER#{email}' into parts."""
    parts: list[_TemplatePart] = []
    pattern = r"\{(\w+)\}|([^{]+)"
    for match in re.finditer(pattern, template):
        if match.group(1):  # placeholder
            parts.append(_TemplatePart(is_placeholder=True, value=match.group(1)))
        else:  # literal
            parts.append(_TemplatePart(is_placeholder=False, value=match.group(2)))
    return parts


def _build_key(parts: list[_TemplatePart], values: dict[str, Any]) -> str:
    """Build key from template parts and values."""
    result = ""
    for part in parts:
        if part.is_placeholder:
            if part.value not in values:
                raise ValueError(f"Missing value for template placeholder: {part.value}")
            result += str(values[part.value])
        else:
            result += part.value
    return result


class StringAttribute(Attribute[str]):
    """String attribute (DynamoDB type S).

    Supports optional template for single-table design patterns.

    Example:
        >>> class User(Model):
        ...     model_config = ModelConfig(table="app")
        ...     pk = StringAttribute(partition_key=True, template="USER#{email}")
        ...     sk = StringAttribute(sort_key=True, template="PROFILE")
        ...     email = StringAttribute()
        ...     name = StringAttribute()
        >>>
        >>> user = User(email="john@example.com", name="John")
        >>> # pk is auto-built as "USER#john@example.com"
    """

    attr_type = "S"

    def __init__(
        self,
        partition_key: bool = False,
        sort_key: bool = False,
        default: str | None = None,
        required: bool = False,
        template: str | None = None,
    ):
        """Create a StringAttribute.

        Args:
            partition_key: True if this is the partition key.
            sort_key: True if this is the sort key.
            default: Default value when not provided.
            required: Whether this field is required.
            template: Template for building key (e.g., "USER#{email}").
        """
        super().__init__(
            partition_key=partition_key, sort_key=sort_key, default=default, required=required
        )
        self.template = template
        self._template_parts: list[_TemplatePart] | None = None
        self._placeholders: list[str] | None = None

        if template:
            self._template_parts = _parse_template(template)
            self._placeholders = [p.value for p in self._template_parts if p.is_placeholder]

    @property
    def has_template(self) -> bool:
        """Check if this attribute has a template."""
        return self.template is not None

    @property
    def placeholders(self) -> list[str]:
        """Get list of placeholder names in the template."""
        return self._placeholders or []

    def build_key(self, values: dict[str, Any]) -> str:
        """Build key value from template and provided values.

        Args:
            values: Dict mapping placeholder names to values.

        Returns:
            The built key string.

        Raises:
            ValueError: If template is not defined or placeholder is missing.
        """
        if not self._template_parts:
            raise ValueError("No template defined for this attribute")
        return _build_key(self._template_parts, values)

    def get_prefix(self) -> str:
        """Get static prefix from template (e.g., 'USER#' from 'USER#{email}').

        Returns:
            The prefix string, or empty string if no template.
        """
        if not self._template_parts:
            return ""
        prefix = ""
        for part in self._template_parts:
            if part.is_placeholder:
                break
            prefix += part.value
        return prefix


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


class ListAttribute(Attribute[list[Any]]):
    """List attribute (DynamoDB type L)."""

    attr_type = "L"


class MapAttribute(Attribute[dict[str, Any]]):
    """Map attribute (DynamoDB type M)."""

    attr_type = "M"
