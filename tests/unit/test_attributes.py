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
    attr = attr_class()
    assert attr.attr_type == expected_type


def test_attribute_hash_key():
    """Attribute can be marked as hash key."""
    attr = StringAttribute(hash_key=True)

    assert attr.hash_key is True
    assert attr.range_key is False


def test_attribute_range_key():
    """Attribute can be marked as range key."""
    attr = StringAttribute(range_key=True)

    assert attr.hash_key is False
    assert attr.range_key is True


def test_attribute_default():
    """Attribute can have a default value."""
    attr = StringAttribute(default="default_value")

    assert attr.default == "default_value"


def test_attribute_null():
    """Attribute null flag controls if None is allowed."""
    nullable = StringAttribute(null=True)
    required = StringAttribute(null=False)

    assert nullable.null is True
    assert required.null is False


def test_attribute_serialize():
    """Attribute serialize returns the value as-is by default."""
    attr = StringAttribute()

    assert attr.serialize("hello") == "hello"


def test_attribute_deserialize():
    """Attribute deserialize returns the value as-is by default."""
    attr = StringAttribute()

    assert attr.deserialize("hello") == "hello"


# --- JSONAttribute tests ---


def test_json_attribute_type():
    """JSONAttribute has string type."""
    attr = JSONAttribute()
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
    attr = JSONAttribute()
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
    attr = JSONAttribute()
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
    attr = EnumAttribute(Status)
    assert attr.attr_type == "S"


def test_enum_attribute_stores_enum_class():
    """EnumAttribute stores the enum class."""
    attr = EnumAttribute(Status)
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
    attr = EnumAttribute(enum_class)
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
    attr = EnumAttribute(enum_class)
    assert attr.deserialize(value) == expected


def test_enum_attribute_with_default():
    """EnumAttribute can have a default value."""
    attr = EnumAttribute(Status, default=Status.PENDING)
    assert attr.default == Status.PENDING


# --- DatetimeAttribute tests ---


def test_datetime_attribute_type():
    """DatetimeAttribute has string type."""
    attr = DatetimeAttribute()
    assert attr.attr_type == "S"


def test_datetime_attribute_serialize_with_timezone():
    """DatetimeAttribute serializes datetime with timezone to ISO string."""
    attr = DatetimeAttribute()
    dt = datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
    result = attr.serialize(dt)
    assert result == "2024-01-15T10:30:00+00:00"


def test_datetime_attribute_serialize_naive():
    """DatetimeAttribute treats naive datetime as UTC."""
    attr = DatetimeAttribute()
    dt = datetime(2024, 1, 15, 10, 30, 0)
    result = attr.serialize(dt)
    assert result == "2024-01-15T10:30:00+00:00"


def test_datetime_attribute_serialize_none():
    """DatetimeAttribute returns None for None."""
    attr = DatetimeAttribute()
    assert attr.serialize(None) is None


def test_datetime_attribute_deserialize():
    """DatetimeAttribute deserializes ISO string to datetime."""
    attr = DatetimeAttribute()
    result = attr.deserialize("2024-01-15T10:30:00+00:00")
    expected = datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
    assert result == expected


def test_datetime_attribute_deserialize_none():
    """DatetimeAttribute returns None for None."""
    attr = DatetimeAttribute()
    assert attr.deserialize(None) is None


def test_datetime_attribute_roundtrip():
    """DatetimeAttribute roundtrip preserves value."""
    attr = DatetimeAttribute()
    original = datetime(2024, 6, 15, 14, 30, 45, tzinfo=timezone.utc)
    serialized = attr.serialize(original)
    deserialized = attr.deserialize(serialized)
    assert deserialized == original


# --- StringSetAttribute tests ---


def test_string_set_attribute_type():
    """StringSetAttribute has SS type."""
    attr = StringSetAttribute()
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
    attr = StringSetAttribute()
    result = attr.serialize(value)
    # Order doesn't matter for sets
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
    attr = StringSetAttribute()
    assert attr.deserialize(value) == expected


# --- NumberSetAttribute tests ---


def test_number_set_attribute_type():
    """NumberSetAttribute has NS type."""
    attr = NumberSetAttribute()
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
    attr = NumberSetAttribute()
    result = attr.serialize(value)
    assert result is not None
    assert len(result) == len(value)
    # All values should be strings
    assert all(isinstance(v, str) for v in result)


def test_number_set_attribute_serialize_empty():
    """NumberSetAttribute returns None for empty set."""
    attr = NumberSetAttribute()
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
    attr = NumberSetAttribute()
    assert attr.deserialize(value) == expected


def test_number_set_attribute_deserialize_preserves_int():
    """NumberSetAttribute returns int for whole numbers."""
    attr = NumberSetAttribute()
    result = attr.deserialize(["1", "2", "3"])
    # All should be int, not float
    assert all(isinstance(v, int) for v in result)


def test_number_set_attribute_roundtrip():
    """NumberSetAttribute roundtrip preserves values."""
    attr = NumberSetAttribute()
    original = {1, 2, 3, 4.5}
    serialized = attr.serialize(original)
    deserialized = attr.deserialize(serialized)
    assert deserialized == original
