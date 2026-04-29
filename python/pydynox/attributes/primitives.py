"""Primitive attribute types (String, Number, Boolean, Binary, List, Map)."""

from __future__ import annotations

import dataclasses
import re
import sys
from dataclasses import dataclass
from typing import Any, Generic, TypeVar, overload

from pydynox.attributes.base import Attribute

MT = TypeVar("MT")


@dataclass
class _TemplatePart:
    """Part of a parsed template."""

    is_placeholder: bool
    value: str  # literal text or attribute name


def _parse_template(template: Any) -> list[_TemplatePart]:
    """Parse template like 'USER#{email}' into parts.

    Supports both regular strings and t-strings (Python 3.14+, PEP 750).

    Args:
        template: String template or Template object (t-string).

    Returns:
        List of template parts.
    """
    # Python 3.14+ t-string support
    if sys.version_info >= (3, 14):
        from string.templatelib import Interpolation, Template

        if isinstance(template, Template):
            parts: list[_TemplatePart] = []
            for item in template:
                if isinstance(item, str):
                    if item:  # skip empty strings
                        parts.append(_TemplatePart(is_placeholder=False, value=item))
                elif isinstance(item, Interpolation):
                    parts.append(_TemplatePart(is_placeholder=True, value=item.expression))
            return parts

    # Regular string template (all Python versions)
    parts = []
    pattern = r"\{(\w+)\}|([^{]+)"
    for match in re.finditer(pattern, str(template)):
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
    On Python 3.14+, t-strings (PEP 750) are also supported.

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

    Python 3.14+ t-string example:
        >>> pk = StringAttribute(partition_key=True, template=t"USER#{email}")
    """

    attr_type = "S"

    def __init__(
        self,
        partition_key: bool = False,
        sort_key: bool = False,
        default: str | None = None,
        required: bool = False,
        template: Any | None = None,
        discriminator: bool = False,
        alias: str | None = None,
    ):
        """Create a StringAttribute.

        Args:
            partition_key: True if this is the partition key.
            sort_key: True if this is the sort key.
            default: Default value when not provided.
            required: Whether this field is required.
            template: Template for building key. Supports strings ("USER#{email}")
                and t-strings (t"USER#{email}") on Python 3.14+.
            discriminator: True if this field is used for model inheritance.
            alias: DynamoDB attribute name override.
        """
        super().__init__(
            partition_key=partition_key,
            sort_key=sort_key,
            default=default,
            required=required,
            discriminator=discriminator,
            alias=alias,
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


class MapAttribute(Attribute[MT], Generic[MT]):
    """Map attribute (DynamoDB type M).

    When used without a model class, stores plain dict.
    When used with a Pydantic model or dataclass, automatically handles
    serialization and deserialization to the typed model.

    Example:
        >>> import dataclasses
        >>> from pydynox import Model, ModelConfig
        >>> from pydynox.attributes import StringAttribute, MapAttribute
        >>>
        >>> @dataclasses.dataclass
        ... class Address:
        ...     street: str
        ...     city: str
        ...     zip: str
        >>>
        >>> class User(Model):
        ...     model_config = ModelConfig(table="users")
        ...     pk = StringAttribute(partition_key=True)
        ...     address = MapAttribute(Address)
        >>>
        >>> user = User(pk="USER#1", address=Address("123 Main St", "NYC", "10001"))
        >>> # address is serialized as DynamoDB Map (M type)
    """

    attr_type = "M"

    @overload
    def __init__(
        self: "MapAttribute[dict[str, Any]]",
        *,
        partition_key: bool = False,
        sort_key: bool = False,
        default: dict[str, Any] | None = None,
        required: bool = False,
        alias: str | None = None,
    ) -> None: ...

    @overload
    def __init__(
        self,
        model_class: type[MT],
        *,
        partition_key: bool = False,
        sort_key: bool = False,
        default: MT | None = None,
        required: bool = False,
        alias: str | None = None,
    ) -> None: ...

    def __init__(
        self,
        model_class: type[MT] | None = None,
        *,
        partition_key: bool = False,
        sort_key: bool = False,
        default: Any | None = None,
        required: bool = False,
        alias: str | None = None,
    ):
        super().__init__(
            partition_key=partition_key,
            sort_key=sort_key,
            default=default,
            required=required,
            alias=alias,
        )
        self.model_class = model_class
        self._is_pydantic = model_class is not None and hasattr(model_class, "model_validate")
        self._is_dataclass = model_class is not None and dataclasses.is_dataclass(model_class)

    def _to_dict(self, value: Any) -> dict[str, Any]:
        """Convert a typed model instance to a dict."""
        if self._is_pydantic:
            return value.model_dump()
        if self._is_dataclass:
            return dataclasses.asdict(value)
        return value

    def _from_dict(self, data: dict[str, Any]) -> Any:
        """Convert a dict to a typed model instance."""
        model_class = self.model_class
        if model_class is None:
            return data
        if self._is_pydantic:
            return model_class.model_validate(data)  # ty: ignore[unresolved-attribute]
        return model_class(**data)

    def serialize(self, value: Any | None) -> dict[str, Any] | None:
        """Convert value to dict for DynamoDB Map storage.

        For typed models, calls model_dump() or dataclasses.asdict() first.

        Args:
            value: Dict or typed model instance to serialize.

        Returns:
            Dict or None.
        """
        if value is None:
            return None
        if self.model_class is not None:
            return self._to_dict(value)
        return value

    def deserialize(self, value: Any) -> Any | None:
        """Convert dict back to typed model or return as-is.

        For typed models, constructs the model from the dict.

        Args:
            value: Dict from DynamoDB.

        Returns:
            Typed model instance, dict, or None.
        """
        if value is None:
            return None
        if self.model_class is not None and isinstance(value, dict):
            return self._from_dict(value)
        return value
