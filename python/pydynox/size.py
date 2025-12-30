"""Item size calculator for DynamoDB.

DynamoDB has a 400KB item size limit. This module helps you check
item sizes before saving to avoid ValidationException errors.

Example:
    >>> user = User(pk="USER#123", name="John", bio="..." * 10000)
    >>> size = user.calculate_size()
    >>> print(f"Item size: {size.bytes} bytes ({size.kb:.2f} KB)")
    >>> if size.is_over_limit:
    ...     print("Too big!")
"""

from dataclasses import dataclass, field
from typing import Any

# DynamoDB item size limit
DYNAMODB_MAX_ITEM_SIZE = 400 * 1024  # 400 KB


@dataclass
class ItemSize:
    """Result of item size calculation.

    Attributes:
        bytes: Total size in bytes.
        kb: Total size in kilobytes.
        percent: Percentage of the 400KB limit used.
        is_over_limit: True if item exceeds 400KB.
        fields: Size breakdown by field (only if detailed=True).
    """

    bytes: int
    fields: dict[str, int] = field(default_factory=dict)

    @property
    def kb(self) -> float:
        """Size in kilobytes."""
        return self.bytes / 1024

    @property
    def percent(self) -> float:
        """Percentage of 400KB limit used."""
        return (self.bytes / DYNAMODB_MAX_ITEM_SIZE) * 100

    @property
    def is_over_limit(self) -> bool:
        """True if item exceeds 400KB limit."""
        return self.bytes > DYNAMODB_MAX_ITEM_SIZE

    def __repr__(self) -> str:
        return f"ItemSize(bytes={self.bytes}, kb={self.kb:.2f}, percent={self.percent:.1f}%)"


def calculate_string_size(value: str) -> int:
    """Calculate size of a string attribute.

    DynamoDB stores strings as UTF-8. Size = byte length of UTF-8 encoding.

    Args:
        value: String value.

    Returns:
        Size in bytes.
    """
    return len(value.encode("utf-8"))


def calculate_number_size(value: float | int) -> int:
    """Calculate size of a number attribute.

    DynamoDB numbers are stored as variable-length. Size depends on
    the number of significant digits.

    Formula: 1 byte + 1 byte per 2 significant digits (rounded up)

    Args:
        value: Number value.

    Returns:
        Size in bytes.
    """
    # Convert to string to count significant digits
    str_value = str(value)

    # Remove sign and decimal point
    digits = str_value.replace("-", "").replace(".", "").lstrip("0")

    if not digits:
        return 1  # Zero

    # 1 byte overhead + 1 byte per 2 digits (rounded up)
    return 1 + (len(digits) + 1) // 2


def calculate_binary_size(value: bytes) -> int:
    """Calculate size of a binary attribute.

    Args:
        value: Binary value.

    Returns:
        Size in bytes.
    """
    return len(value)


def calculate_boolean_size(_value: bool) -> int:
    """Calculate size of a boolean attribute.

    Booleans are always 1 byte.

    Args:
        value: Boolean value.

    Returns:
        Size in bytes (always 1).
    """
    return 1


def calculate_null_size() -> int:
    """Calculate size of a null attribute.

    Nulls are always 1 byte.

    Returns:
        Size in bytes (always 1).
    """
    return 1


def calculate_list_size(value: list) -> int:
    """Calculate size of a list attribute.

    List overhead: 3 bytes + size of each element.

    Args:
        value: List value.

    Returns:
        Size in bytes.
    """
    size = 3  # List overhead
    for item in value:
        size += calculate_attribute_size(item)
    return size


def calculate_map_size(value: dict) -> int:
    """Calculate size of a map attribute.

    Map overhead: 3 bytes + size of each key-value pair.
    Keys are strings, so they add their UTF-8 byte length.

    Args:
        value: Dict value.

    Returns:
        Size in bytes.
    """
    size = 3  # Map overhead
    for key, val in value.items():
        size += calculate_string_size(key)  # Key name
        size += calculate_attribute_size(val)  # Value
    return size


def calculate_set_size(value: set, element_type: str = "S") -> int:
    """Calculate size of a set attribute.

    Set overhead: 3 bytes + size of each element.

    Args:
        value: Set value.
        element_type: Type of elements ("S", "N", or "B").

    Returns:
        Size in bytes.
    """
    size = 3  # Set overhead
    for item in value:
        if element_type == "S":
            size += calculate_string_size(item)
        elif element_type == "N":
            size += calculate_number_size(item)
        elif element_type == "B":
            size += calculate_binary_size(item)
    return size


def calculate_attribute_size(value: Any) -> int:
    """Calculate size of any attribute value.

    Detects the type and calls the right calculator.

    Args:
        value: Any DynamoDB-compatible value.

    Returns:
        Size in bytes.
    """
    if value is None:
        return calculate_null_size()
    elif isinstance(value, bool):
        # Must check bool before int (bool is subclass of int)
        return calculate_boolean_size(value)
    elif isinstance(value, str):
        return calculate_string_size(value)
    elif isinstance(value, (int, float)):
        return calculate_number_size(value)
    elif isinstance(value, bytes):
        return calculate_binary_size(value)
    elif isinstance(value, list):
        return calculate_list_size(value)
    elif isinstance(value, dict):
        return calculate_map_size(value)
    elif isinstance(value, set):
        # Detect element type from first element
        if not value:
            return 3  # Empty set
        first = next(iter(value))
        if isinstance(first, str):
            return calculate_set_size(value, "S")
        elif isinstance(first, (int, float)):
            return calculate_set_size(value, "N")
        elif isinstance(first, bytes):
            return calculate_set_size(value, "B")
        return 3  # Unknown set type
    else:
        # Unknown type, try string conversion
        return calculate_string_size(str(value))


def calculate_item_size(item: dict[str, Any], detailed: bool = False) -> ItemSize:
    """Calculate total size of a DynamoDB item.

    Args:
        item: Dict with attribute names and values.
        detailed: If True, include per-field breakdown.

    Returns:
        ItemSize with total bytes and optional field breakdown.

    Example:
        >>> item = {"pk": "USER#123", "name": "John", "age": 30}
        >>> size = calculate_item_size(item)
        >>> print(f"{size.bytes} bytes")
    """
    total = 0
    fields: dict[str, int] = {}

    for attr_name, value in item.items():
        # Attribute name size (UTF-8 encoded)
        name_size = calculate_string_size(attr_name)
        # Attribute value size
        value_size = calculate_attribute_size(value)
        # Total for this attribute
        attr_size = name_size + value_size

        total += attr_size

        if detailed:
            fields[attr_name] = attr_size

    if detailed:
        return ItemSize(bytes=total, fields=fields)
    return ItemSize(bytes=total)
