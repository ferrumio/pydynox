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
    # WHEN creating an ItemSize with 1KB
    size = ItemSize(bytes=1024)

    # THEN properties are calculated correctly
    assert size.kb == 1.0
    assert size.percent == pytest.approx(0.25, rel=0.01)
    assert size.is_over_limit is False

    # WHEN creating an ItemSize over the limit
    big_size = ItemSize(bytes=DYNAMODB_MAX_ITEM_SIZE + 1)

    # THEN is_over_limit is True
    assert big_size.is_over_limit is True


def test_string_size():
    """String size is UTF-8 byte length."""
    # THEN string size equals UTF-8 byte length
    assert calculate_string_size("hello") == 5
    assert calculate_string_size("") == 0
    # UTF-8 multi-byte chars (3 bytes each)
    assert calculate_string_size("日本語") == 9


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
    # THEN binary size equals byte length
    assert calculate_binary_size(b"hello") == 5
    assert calculate_binary_size(b"") == 0


def test_boolean_size():
    """Boolean is always 1 byte."""
    # THEN boolean size is always 1
    assert calculate_boolean_size(True) == 1
    assert calculate_boolean_size(False) == 1


def test_null_size():
    """Null is always 1 byte."""
    # THEN null size is always 1
    assert calculate_null_size() == 1


def test_list_size():
    """List has 3 byte overhead plus element sizes."""
    # THEN empty list has 3 byte overhead
    assert calculate_list_size([]) == 3

    # THEN list with strings: 3 (overhead) + 5 (hello) + 5 (world) = 13
    assert calculate_list_size(["hello", "world"]) == 13


def test_map_size():
    """Map has 3 byte overhead plus key-value sizes."""
    # THEN empty map has 3 byte overhead
    assert calculate_map_size({}) == 3

    # THEN map with string: 3 (overhead) + 4 (name) + 4 (John) = 11
    assert calculate_map_size({"name": "John"}) == 11


def test_set_size():
    """Set has 3 byte overhead plus element sizes."""
    # THEN string set: 3 + 1 + 1 = 5
    assert calculate_set_size({"a", "b"}, "S") == 5

    # THEN number set: 3 + 2 + 2 = 7
    assert calculate_set_size({1, 2}, "N") == 7


def test_calculate_attribute_size_detects_types():
    """calculate_attribute_size handles all types."""
    # THEN each type returns correct size
    assert calculate_attribute_size(None) == 1
    assert calculate_attribute_size(True) == 1
    assert calculate_attribute_size("hi") == 2
    assert calculate_attribute_size(42) == 2
    assert calculate_attribute_size(b"x") == 1
    assert calculate_attribute_size([]) == 3
    assert calculate_attribute_size({}) == 3


def test_calculate_item_size_basic():
    """calculate_item_size sums all attribute sizes."""
    # GIVEN an item with two string attributes
    item = {"pk": "USER#123", "name": "John"}

    # WHEN calculating size
    size = calculate_item_size(item)

    # THEN size is sum of all attributes
    # pk: 2 (name) + 8 (value) = 10
    # name: 4 (name) + 4 (value) = 8
    # total = 18
    assert size.bytes == 18
    assert size.fields == {}  # Not detailed


def test_calculate_item_size_detailed():
    """calculate_item_size with detailed=True returns field breakdown."""
    # GIVEN an item with two attributes
    item = {"pk": "USER#123", "name": "John"}

    # WHEN calculating size with detailed=True
    size = calculate_item_size(item, detailed=True)

    # THEN field breakdown is included
    assert size.bytes == 18
    assert size.fields == {"pk": 10, "name": 8}


def test_calculate_item_size_nested():
    """calculate_item_size handles nested structures."""
    # GIVEN an item with nested map and list
    item = {
        "pk": "USER#1",
        "data": {
            "tags": ["a", "b"],
        },
    }

    # WHEN calculating size
    size = calculate_item_size(item)

    # THEN nested structures are included
    # pk: 2 + 6 = 8
    # data: 4 + (3 + 4 + (3 + 1 + 1)) = 4 + 12 = 16
    assert size.bytes == 24


def test_item_too_large_error_on_save(monkeypatch):
    """Model.save() raises ItemTooLargeException when item exceeds max_size."""
    from unittest.mock import MagicMock

    from pydynox import Model, ModelConfig
    from pydynox.attributes import StringAttribute
    from pydynox.exceptions import ItemTooLargeException

    # GIVEN a model with max_size=100 and an item larger than that
    mock_client = MagicMock()

    class User(Model):
        model_config = ModelConfig(table="users", client=mock_client, max_size=100)
        pk = StringAttribute(hash_key=True)
        bio = StringAttribute()

    User._client_instance = None
    user = User(pk="USER#123", bio="x" * 200)

    # WHEN saving the item
    # THEN ItemTooLargeException is raised with size details
    with pytest.raises(ItemTooLargeException) as exc_info:
        user.save()

    assert exc_info.value.size > 100
    assert exc_info.value.max_size == 100
    assert exc_info.value.item_key == {"pk": "USER#123"}
