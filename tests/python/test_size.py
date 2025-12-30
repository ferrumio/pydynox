"""Tests for item size calculator."""

import pytest
from pydynox.size import (
    DYNAMODB_MAX_ITEM_SIZE,
    ItemSize,
    calculate_attribute_size,
    calculate_binary_size,
    calculate_boolean_size,
    calculate_item_size,
    calculate_list_size,
    calculate_map_size,
    calculate_null_size,
    calculate_number_size,
    calculate_set_size,
    calculate_string_size,
)


def test_item_size_properties():
    """ItemSize calculates kb, percent, and is_over_limit correctly."""
    size = ItemSize(bytes=1024)
    assert size.kb == 1.0
    assert size.percent == pytest.approx(0.25, rel=0.01)
    assert size.is_over_limit is False

    # Over limit
    big_size = ItemSize(bytes=DYNAMODB_MAX_ITEM_SIZE + 1)
    assert big_size.is_over_limit is True


def test_string_size():
    """String size is UTF-8 byte length."""
    assert calculate_string_size("hello") == 5
    assert calculate_string_size("") == 0
    # UTF-8 multi-byte chars
    assert calculate_string_size("日本語") == 9  # 3 bytes each


@pytest.mark.parametrize(
    "value,expected",
    [
        pytest.param(0, 1, id="zero"),
        pytest.param(1, 2, id="single_digit"),
        pytest.param(12, 2, id="two_digits"),
        pytest.param(123, 3, id="three_digits"),
        pytest.param(1234, 3, id="four_digits"),
        pytest.param(-123, 3, id="negative"),
        pytest.param(3.14, 3, id="decimal"),
    ],
)
def test_number_size(value, expected):
    """Number size depends on significant digits."""
    assert calculate_number_size(value) == expected


def test_binary_size():
    """Binary size is byte length."""
    assert calculate_binary_size(b"hello") == 5
    assert calculate_binary_size(b"") == 0


def test_boolean_size():
    """Boolean is always 1 byte."""
    assert calculate_boolean_size(True) == 1
    assert calculate_boolean_size(False) == 1


def test_null_size():
    """Null is always 1 byte."""
    assert calculate_null_size() == 1


def test_list_size():
    """List has 3 byte overhead plus element sizes."""
    # Empty list
    assert calculate_list_size([]) == 3

    # List with strings
    # 3 (overhead) + 5 (hello) + 5 (world)
    assert calculate_list_size(["hello", "world"]) == 13


def test_map_size():
    """Map has 3 byte overhead plus key-value sizes."""
    # Empty map
    assert calculate_map_size({}) == 3

    # Map with string values
    # 3 (overhead) + 4 (name) + 4 (John)
    assert calculate_map_size({"name": "John"}) == 11


def test_set_size():
    """Set has 3 byte overhead plus element sizes."""
    # String set
    assert calculate_set_size({"a", "b"}, "S") == 5  # 3 + 1 + 1

    # Number set
    assert calculate_set_size({1, 2}, "N") == 7  # 3 + 2 + 2


def test_calculate_attribute_size_detects_types():
    """calculate_attribute_size handles all types."""
    assert calculate_attribute_size(None) == 1
    assert calculate_attribute_size(True) == 1
    assert calculate_attribute_size("hi") == 2
    assert calculate_attribute_size(42) == 2
    assert calculate_attribute_size(b"x") == 1
    assert calculate_attribute_size([]) == 3
    assert calculate_attribute_size({}) == 3


def test_calculate_item_size_basic():
    """calculate_item_size sums all attribute sizes."""
    item = {"pk": "USER#123", "name": "John"}
    size = calculate_item_size(item)

    # pk: 2 (name) + 8 (value) = 10
    # name: 4 (name) + 4 (value) = 8
    # total = 18
    assert size.bytes == 18
    assert size.fields == {}  # Not detailed


def test_calculate_item_size_detailed():
    """calculate_item_size with detailed=True returns field breakdown."""
    item = {"pk": "USER#123", "name": "John"}
    size = calculate_item_size(item, detailed=True)

    assert size.bytes == 18
    assert size.fields == {"pk": 10, "name": 8}


def test_calculate_item_size_nested():
    """calculate_item_size handles nested structures."""
    item = {
        "pk": "USER#1",
        "data": {
            "tags": ["a", "b"],
        },
    }
    size = calculate_item_size(item)

    # pk: 2 + 6 = 8
    # data: 4 + (3 + 4 + (3 + 1 + 1)) = 4 + 12 = 16
    assert size.bytes == 24


def test_item_too_large_error_on_save(monkeypatch):
    """Model.save() raises ItemTooLargeError when item exceeds max_size."""
    from pydynox import Model
    from pydynox.attributes import StringAttribute
    from pydynox.exceptions import ItemTooLargeError

    class User(Model):
        class Meta:
            table = "users"
            max_size = 100  # Very small limit for testing

        pk = StringAttribute(hash_key=True)
        bio = StringAttribute()

    # Mock the client so we don't hit DynamoDB
    monkeypatch.setattr(User, "_get_client", lambda cls: None)

    user = User(pk="USER#123", bio="x" * 200)

    with pytest.raises(ItemTooLargeError) as exc_info:
        user.save()

    assert exc_info.value.size > 100
    assert exc_info.value.max_size == 100
    assert exc_info.value.item_key == {"pk": "USER#123"}
