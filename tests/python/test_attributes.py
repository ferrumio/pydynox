"""Tests for attribute types."""

import pytest
from pydynox.attributes import (  # noqa: I001
    BinaryAttribute,
    BooleanAttribute,
    ListAttribute,
    MapAttribute,
    NumberAttribute,
    StringAttribute,
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
