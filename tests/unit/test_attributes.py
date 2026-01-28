"""Tests for attribute types."""

from datetime import datetime, timezone
from enum import Enum

import pytest
from pydynox.attributes import (  # noqa: I001
    BinaryAttribute,
    BooleanAttribute,
    DatetimeAttribute,
    EnumAttribute,
    JSONAttribute,
    ListAttribute,
    MapAttribute,
    NumberAttribute,
    NumberSetAttribute,
    StringAttribute,
    StringSetAttribute,
)


@pytest.mark.parametrize(
    "attr_class,expected_type",
    [
        pytest.param(StringAttribute, "S", id="string"),
        pytest.param(NumberAttribute, "N", id="number"),
        pytest.param(BooleanAttribute, "BOOL", id="boolean"),
        pytest.param(BinaryAttribute, "B", id="binary"),
        pytest.param(ListAttribute, "L", id="list"),
        pytest.param(MapAttribute, "M", id="map"),
    ],
)
def test_attribute_types(attr_class, expected_type):
    """Each attribute class has the correct DynamoDB type."""
    # WHEN we create an attribute
    attr = attr_class()

    # THEN attr_type should match expected
    assert attr.attr_type == expected_type


def test_attribute_hash_key():
    """Attribute can be marked as hash key."""
    # WHEN we create an attribute with hash_key=True
    attr = StringAttribute(hash_key=True)

    # THEN hash_key should be True and range_key False
    assert attr.hash_key is True
    assert attr.range_key is False


def test_attribute_range_key():
    """Attribute can be marked as range key."""
    # WHEN we create an attribute with range_key=True
    attr = StringAttribute(range_key=True)

    # THEN range_key should be True and hash_key False
    assert attr.hash_key is False
    assert attr.range_key is True


def test_attribute_default():
    """Attribute can have a default value."""
    # WHEN we create an attribute with a default
    attr = StringAttribute(default="default_value")

    # THEN default should be set
    assert attr.default == "default_value"


def test_attribute_required():
    """Attribute required flag controls if None is allowed."""
    # WHEN we create optional and required attributes
    optional = StringAttribute(required=False)
    required = StringAttribute(required=True)

    # THEN required flag should be set correctly
    assert optional.required is False
    assert required.required is True


def test_attribute_serialize():
    """Attribute serialize returns the value as-is by default."""
    # GIVEN a string attribute
    attr = StringAttribute()

    # WHEN we serialize a value
    # THEN it should be returned as-is
    assert attr.serialize("hello") == "hello"


def test_attribute_deserialize():
    """Attribute deserialize returns the value as-is by default."""
    # GIVEN a string attribute
    attr = StringAttribute()

    # WHEN we deserialize a value
    # THEN it should be returned as-is
    assert attr.deserialize("hello") == "hello"


# --- JSONAttribute tests ---


def test_json_attribute_type():
    """JSONAttribute has string type."""
    # WHEN we create a JSON attribute
    attr = JSONAttribute()

    # THEN attr_type should be string
    assert attr.attr_type == "S"


@pytest.mark.parametrize(
    "value,expected",
    [
        pytest.param({"key": "value"}, '{"key": "value"}', id="dict"),
        pytest.param(["a", "b", "c"], '["a", "b", "c"]', id="list"),
        pytest.param({"nested": {"a": 1}}, '{"nested": {"a": 1}}', id="nested"),
        pytest.param(None, None, id="none"),
    ],
)
def test_json_attribute_serialize(value, expected):
    """JSONAttribute serializes dict/list to JSON string."""
    # GIVEN a JSON attribute
    attr = JSONAttribute()

    # WHEN we serialize the value
    # THEN it should match expected JSON string
    assert attr.serialize(value) == expected


@pytest.mark.parametrize(
    "value,expected",
    [
        pytest.param('{"key": "value"}', {"key": "value"}, id="dict"),
        pytest.param('["a", "b", "c"]', ["a", "b", "c"], id="list"),
        pytest.param(None, None, id="none"),
        pytest.param({"already": "dict"}, {"already": "dict"}, id="passthrough_dict"),
    ],
)
def test_json_attribute_deserialize(value, expected):
    """JSONAttribute deserializes JSON string to dict/list."""
    # GIVEN a JSON attribute
    attr = JSONAttribute()

    # WHEN we deserialize the value
    # THEN it should match expected Python object
    assert attr.deserialize(value) == expected


# --- EnumAttribute tests ---


class Status(Enum):
    PENDING = "pending"
    ACTIVE = "active"
    INACTIVE = "inactive"


class Priority(Enum):
    LOW = 1
    MEDIUM = 2
    HIGH = 3


def test_enum_attribute_type():
    """EnumAttribute has string type."""
    # WHEN we create an enum attribute
    attr = EnumAttribute(Status)

    # THEN attr_type should be string
    assert attr.attr_type == "S"


def test_enum_attribute_stores_enum_class():
    """EnumAttribute stores the enum class."""
    # WHEN we create an enum attribute
    attr = EnumAttribute(Status)

    # THEN enum_class should be stored
    assert attr.enum_class is Status


@pytest.mark.parametrize(
    "enum_class,value,expected",
    [
        pytest.param(Status, Status.ACTIVE, "active", id="string_enum"),
        pytest.param(Priority, Priority.HIGH, "3", id="int_enum"),
        pytest.param(Status, None, None, id="none"),
    ],
)
def test_enum_attribute_serialize(enum_class, value, expected):
    """EnumAttribute serializes enum to its value."""
    # GIVEN an enum attribute
    attr = EnumAttribute(enum_class)

    # WHEN we serialize the enum
    # THEN it should return the enum's value
    assert attr.serialize(value) == expected


@pytest.mark.parametrize(
    "enum_class,value,expected",
    [
        pytest.param(Status, "active", Status.ACTIVE, id="string_enum"),
        pytest.param(Priority, 2, Priority.MEDIUM, id="int_enum"),
        pytest.param(Status, None, None, id="none"),
    ],
)
def test_enum_attribute_deserialize(enum_class, value, expected):
    """EnumAttribute deserializes value to enum."""
    # GIVEN an enum attribute
    attr = EnumAttribute(enum_class)

    # WHEN we deserialize the value
    # THEN it should return the enum member
    assert attr.deserialize(value) == expected


def test_enum_attribute_with_default():
    """EnumAttribute can have a default value."""
    # WHEN we create an enum attribute with default
    attr = EnumAttribute(Status, default=Status.PENDING)

    # THEN default should be set
    assert attr.default == Status.PENDING


# --- DatetimeAttribute tests ---


def test_datetime_attribute_type():
    """DatetimeAttribute has string type."""
    # WHEN we create a datetime attribute
    attr = DatetimeAttribute()

    # THEN attr_type should be string
    assert attr.attr_type == "S"


def test_datetime_attribute_serialize_with_timezone():
    """DatetimeAttribute serializes datetime with timezone to ISO string."""
    # GIVEN a datetime attribute and a datetime with timezone
    attr = DatetimeAttribute()
    dt = datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc)

    # WHEN we serialize
    result = attr.serialize(dt)

    # THEN it should be ISO format
    assert result == "2024-01-15T10:30:00+00:00"


def test_datetime_attribute_serialize_naive():
    """DatetimeAttribute treats naive datetime as UTC."""
    # GIVEN a datetime attribute and a naive datetime
    attr = DatetimeAttribute()
    dt = datetime(2024, 1, 15, 10, 30, 0)

    # WHEN we serialize
    result = attr.serialize(dt)

    # THEN it should be treated as UTC
    assert result == "2024-01-15T10:30:00+00:00"


def test_datetime_attribute_serialize_none():
    """DatetimeAttribute returns None for None."""
    # GIVEN a datetime attribute
    attr = DatetimeAttribute()

    # WHEN we serialize None
    # THEN None should be returned
    assert attr.serialize(None) is None


def test_datetime_attribute_deserialize():
    """DatetimeAttribute deserializes ISO string to datetime."""
    # GIVEN a datetime attribute and an ISO string
    attr = DatetimeAttribute()

    # WHEN we deserialize
    result = attr.deserialize("2024-01-15T10:30:00+00:00")

    # THEN it should be a datetime with timezone
    expected = datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
    assert result == expected


def test_datetime_attribute_deserialize_none():
    """DatetimeAttribute returns None for None."""
    # GIVEN a datetime attribute
    attr = DatetimeAttribute()

    # WHEN we deserialize None
    # THEN None should be returned
    assert attr.deserialize(None) is None


def test_datetime_attribute_roundtrip():
    """DatetimeAttribute roundtrip preserves value."""
    # GIVEN a datetime attribute and original datetime
    attr = DatetimeAttribute()
    original = datetime(2024, 6, 15, 14, 30, 45, tzinfo=timezone.utc)

    # WHEN we serialize and deserialize
    serialized = attr.serialize(original)
    deserialized = attr.deserialize(serialized)

    # THEN original value should be preserved
    assert deserialized == original


# --- StringSetAttribute tests ---


def test_string_set_attribute_type():
    """StringSetAttribute has SS type."""
    # WHEN we create a string set attribute
    attr = StringSetAttribute()

    # THEN attr_type should be SS
    assert attr.attr_type == "SS"


@pytest.mark.parametrize(
    "value,expected",
    [
        pytest.param({"a", "b", "c"}, ["a", "b", "c"], id="set"),
        pytest.param(set(), None, id="empty_set"),
        pytest.param(None, None, id="none"),
    ],
)
def test_string_set_attribute_serialize(value, expected):
    """StringSetAttribute serializes set to list."""
    # GIVEN a string set attribute
    attr = StringSetAttribute()

    # WHEN we serialize
    result = attr.serialize(value)

    # THEN it should match expected (order doesn't matter for sets)
    if result is not None and expected is not None:
        assert set(result) == set(expected)
    else:
        assert result == expected


@pytest.mark.parametrize(
    "value,expected",
    [
        pytest.param(["a", "b", "c"], {"a", "b", "c"}, id="list"),
        pytest.param(None, set(), id="none"),
        pytest.param([], set(), id="empty_list"),
    ],
)
def test_string_set_attribute_deserialize(value, expected):
    """StringSetAttribute deserializes list to set."""
    # GIVEN a string set attribute
    attr = StringSetAttribute()

    # WHEN we deserialize
    # THEN it should match expected set
    assert attr.deserialize(value) == expected


# --- NumberSetAttribute tests ---


def test_number_set_attribute_type():
    """NumberSetAttribute has NS type."""
    # WHEN we create a number set attribute
    attr = NumberSetAttribute()

    # THEN attr_type should be NS
    assert attr.attr_type == "NS"


@pytest.mark.parametrize(
    "value",
    [
        pytest.param({1, 2, 3}, id="integers"),
        pytest.param({1.5, 2.5, 3.5}, id="floats"),
        pytest.param({1, 2.5, 3}, id="mixed"),
    ],
)
def test_number_set_attribute_serialize(value):
    """NumberSetAttribute serializes set to list of strings."""
    # GIVEN a number set attribute
    attr = NumberSetAttribute()

    # WHEN we serialize
    result = attr.serialize(value)

    # THEN result should be list of strings with same length
    assert result is not None
    assert len(result) == len(value)
    assert all(isinstance(v, str) for v in result)


def test_number_set_attribute_serialize_empty():
    """NumberSetAttribute returns None for empty set."""
    # GIVEN a number set attribute
    attr = NumberSetAttribute()

    # WHEN we serialize empty set or None
    # THEN None should be returned
    assert attr.serialize(set()) is None
    assert attr.serialize(None) is None


@pytest.mark.parametrize(
    "value,expected",
    [
        pytest.param(["1", "2", "3"], {1, 2, 3}, id="integers"),
        pytest.param(["1.5", "2.5"], {1.5, 2.5}, id="floats"),
        pytest.param(None, set(), id="none"),
    ],
)
def test_number_set_attribute_deserialize(value, expected):
    """NumberSetAttribute deserializes list of strings to set of numbers."""
    # GIVEN a number set attribute
    attr = NumberSetAttribute()

    # WHEN we deserialize
    # THEN it should match expected set
    assert attr.deserialize(value) == expected


def test_number_set_attribute_deserialize_preserves_int():
    """NumberSetAttribute returns int for whole numbers."""
    # GIVEN a number set attribute
    attr = NumberSetAttribute()

    # WHEN we deserialize whole numbers
    result = attr.deserialize(["1", "2", "3"])

    # THEN all should be int, not float
    assert all(isinstance(v, int) for v in result)


def test_number_set_attribute_roundtrip():
    """NumberSetAttribute roundtrip preserves values."""
    # GIVEN a number set attribute and original set
    attr = NumberSetAttribute()
    original = {1, 2, 3, 4.5}

    # WHEN we serialize and deserialize
    serialized = attr.serialize(original)
    deserialized = attr.deserialize(serialized)

    # THEN original values should be preserved
    assert deserialized == original
