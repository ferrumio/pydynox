"""Tests for condition classes."""

import pytest
from pydynox.attributes import (
    ListAttribute,
    MapAttribute,
    NumberAttribute,
    StringAttribute,
)
from pydynox.conditions import And, Not, Or


def make_attr(cls, name):
    """Create test attribute with name set."""
    attr = cls()
    attr.attr_name = name
    return attr


# Comparison operators


def test_eq():
    """Test equality condition."""
    # GIVEN a name attribute
    name = make_attr(StringAttribute, "name")

    # WHEN we create an equality condition
    cond = name == "John"

    # THEN serialization should produce correct expression
    names: dict = {}
    values: dict = {}
    result = cond.serialize(names, values)

    assert result == "#n0 = :v0"
    assert names == {"name": "#n0"}
    assert values == {":v0": "John"}


def test_ne():
    """Test not-equal condition."""
    # GIVEN a status attribute
    status = make_attr(StringAttribute, "status")

    # WHEN we create a not-equal condition
    cond = status != "deleted"

    # THEN serialization should produce correct expression
    names: dict = {}
    values: dict = {}
    result = cond.serialize(names, values)

    assert result == "#n0 <> :v0"


def test_gt():
    """Test greater-than condition."""
    # GIVEN an age attribute
    age = make_attr(NumberAttribute, "age")

    # WHEN we create a greater-than condition
    cond = age > 18

    # THEN serialization should produce correct expression
    names: dict = {}
    values: dict = {}
    result = cond.serialize(names, values)

    assert result == "#n0 > :v0"
    assert values == {":v0": 18}


def test_ge():
    """Test greater-than-or-equal condition."""
    # GIVEN an age attribute
    age = make_attr(NumberAttribute, "age")

    # WHEN we create a >= condition
    cond = age >= 21

    # THEN serialization should produce correct expression
    names: dict = {}
    values: dict = {}
    result = cond.serialize(names, values)

    assert result == "#n0 >= :v0"


def test_lt():
    """Test less-than condition."""
    # GIVEN a price attribute
    price = make_attr(NumberAttribute, "price")

    # WHEN we create a less-than condition
    cond = price < 100

    # THEN serialization should produce correct expression
    names: dict = {}
    values: dict = {}
    result = cond.serialize(names, values)

    assert result == "#n0 < :v0"


def test_le():
    """Test less-than-or-equal condition."""
    # GIVEN a price attribute
    price = make_attr(NumberAttribute, "price")

    # WHEN we create a <= condition
    cond = price <= 50

    # THEN serialization should produce correct expression
    names: dict = {}
    values: dict = {}
    result = cond.serialize(names, values)

    assert result == "#n0 <= :v0"


# Function conditions


def test_exists():
    """Test attribute_exists condition."""
    # GIVEN an email attribute
    email = make_attr(StringAttribute, "email")

    # WHEN we create an exists condition
    cond = email.exists()

    # THEN serialization should produce correct expression
    names: dict = {}
    values: dict = {}
    result = cond.serialize(names, values)

    assert result == "attribute_exists(#n0)"
    assert names == {"email": "#n0"}


def test_does_not_exist():
    """Test attribute_not_exists condition."""
    # GIVEN a deleted_at attribute
    deleted = make_attr(StringAttribute, "deleted_at")

    # WHEN we create a does_not_exist condition
    cond = deleted.not_exists()

    # THEN serialization should produce correct expression
    names: dict = {}
    values: dict = {}
    result = cond.serialize(names, values)

    assert result == "attribute_not_exists(#n0)"


def test_begins_with():
    """Test begins_with condition."""
    # GIVEN a sk attribute
    sk = make_attr(StringAttribute, "sk")

    # WHEN we create a begins_with condition
    cond = sk.begins_with("ORDER#")

    # THEN serialization should produce correct expression
    names: dict = {}
    values: dict = {}
    result = cond.serialize(names, values)

    assert result == "begins_with(#n0, :v0)"
    assert values == {":v0": "ORDER#"}


def test_contains():
    """Test contains condition."""
    # GIVEN a tags attribute
    tags = make_attr(ListAttribute, "tags")

    # WHEN we create a contains condition
    cond = tags.contains("premium")

    # THEN serialization should produce correct expression
    names: dict = {}
    values: dict = {}
    result = cond.serialize(names, values)

    assert result == "contains(#n0, :v0)"


def test_between():
    """Test between condition."""
    # GIVEN an age attribute
    age = make_attr(NumberAttribute, "age")

    # WHEN we create a between condition
    cond = age.between(18, 65)

    # THEN serialization should produce correct expression
    names: dict = {}
    values: dict = {}
    result = cond.serialize(names, values)

    assert result == "#n0 BETWEEN :v0 AND :v1"
    assert values == {":v0": 18, ":v1": 65}


def test_is_in():
    """Test IN condition."""
    # GIVEN a status attribute
    status = make_attr(StringAttribute, "status")

    # WHEN we create an is_in condition
    cond = status.is_in("active", "pending", "review")

    # THEN serialization should produce correct expression
    names: dict = {}
    values: dict = {}
    result = cond.serialize(names, values)

    assert result == "#n0 IN (:v0, :v1, :v2)"
    assert values == {":v0": "active", ":v1": "pending", ":v2": "review"}


# Combined conditions


def test_and_operator():
    """Test AND operator with &."""
    # GIVEN age and status attributes
    age = make_attr(NumberAttribute, "age")
    status = make_attr(StringAttribute, "status")

    # WHEN we combine conditions with &
    cond = (age > 18) & (status == "active")

    # THEN serialization should produce correct expression
    names: dict = {}
    values: dict = {}
    result = cond.serialize(names, values)

    assert result == "(#n0 > :v0 AND #n1 = :v1)"
    assert names == {"age": "#n0", "status": "#n1"}


def test_or_operator():
    """Test OR operator with |."""
    # GIVEN a status attribute
    status = make_attr(StringAttribute, "status")

    # WHEN we combine conditions with |
    cond = (status == "active") | (status == "pending")

    # THEN serialization should produce correct expression
    names: dict = {}
    values: dict = {}
    result = cond.serialize(names, values)

    assert result == "(#n0 = :v0 OR #n0 = :v1)"


def test_not_operator():
    """Test NOT operator with ~."""
    # GIVEN a deleted attribute
    deleted = make_attr(StringAttribute, "deleted")

    # WHEN we negate a condition with ~
    cond = ~deleted.exists()

    # THEN serialization should produce correct expression
    names: dict = {}
    values: dict = {}
    result = cond.serialize(names, values)

    assert result == "(NOT attribute_exists(#n0))"


def test_complex_combination():
    """Test complex combination of conditions."""
    # GIVEN multiple attributes
    age = make_attr(NumberAttribute, "age")
    status = make_attr(StringAttribute, "status")
    deleted = make_attr(StringAttribute, "deleted")

    # WHEN we create a complex condition
    cond = ((age > 18) & (status == "active")) | ~deleted.exists()

    # THEN serialization should produce correct expression
    names: dict = {}
    values: dict = {}
    result = cond.serialize(names, values)

    assert result == "((#n0 > :v0 AND #n1 = :v1) OR (NOT attribute_exists(#n2)))"


# Nested access


def test_map_access():
    """Test nested map access in conditions."""
    # GIVEN an address map attribute
    address = make_attr(MapAttribute, "address")

    # WHEN we access a nested key
    cond = address["city"] == "NYC"

    # THEN serialization should produce correct expression
    names: dict = {}
    values: dict = {}
    result = cond.serialize(names, values)

    assert result == "#n0.#n1 = :v0"
    assert names == {"address": "#n0", "city": "#n1"}


def test_list_access():
    """Test list index access in conditions."""
    # GIVEN a tags list attribute
    tags = make_attr(ListAttribute, "tags")

    # WHEN we access by index
    cond = tags[0] == "premium"

    # THEN serialization should produce correct expression
    names: dict = {}
    values: dict = {}
    result = cond.serialize(names, values)

    assert result == "#n0[0] = :v0"


def test_deep_nested():
    """Test deep nested access in conditions."""
    # GIVEN a data map attribute
    data = make_attr(MapAttribute, "data")

    # WHEN we access deeply nested path
    cond = data["users"][0]["name"] == "John"

    # THEN serialization should produce correct expression
    names: dict = {}
    values: dict = {}
    result = cond.serialize(names, values)

    assert result == "#n0.#n1[0].#n2 = :v0"


# And, Or, Not functions


def test_and_function():
    """Test And() function with multiple conditions."""
    # GIVEN multiple attributes
    age = make_attr(NumberAttribute, "age")
    status = make_attr(StringAttribute, "status")
    active = make_attr(StringAttribute, "active")

    # WHEN we use And() function
    cond = And(age > 18, status == "active", active == True)  # noqa: E712

    # THEN serialization should produce correct expression
    names: dict = {}
    values: dict = {}
    result = cond.serialize(names, values)

    assert result == "((#n0 > :v0 AND #n1 = :v1) AND #n2 = :v2)"


def test_or_function():
    """Test Or() function with multiple conditions."""
    # GIVEN a status attribute
    status = make_attr(StringAttribute, "status")

    # WHEN we use Or() function
    cond = Or(status == "a", status == "b", status == "c")

    # THEN serialization should produce correct expression
    names: dict = {}
    values: dict = {}
    result = cond.serialize(names, values)

    assert result == "((#n0 = :v0 OR #n0 = :v1) OR #n0 = :v2)"


def test_not_function():
    """Test Not() function."""
    # GIVEN a deleted attribute
    deleted = make_attr(StringAttribute, "deleted")

    # WHEN we use Not() function
    cond = Not(deleted.exists())

    # THEN serialization should produce correct expression
    names: dict = {}
    values: dict = {}
    result = cond.serialize(names, values)

    assert result == "(NOT attribute_exists(#n0))"


def test_and_requires_two_conditions():
    """Test And() requires at least 2 conditions."""
    # GIVEN an age attribute
    age = make_attr(NumberAttribute, "age")

    # WHEN we try to create And with one condition
    # THEN ValueError should be raised
    with pytest.raises(ValueError, match="at least 2"):
        And(age > 18)


def test_or_requires_two_conditions():
    """Test Or() requires at least 2 conditions."""
    # GIVEN an age attribute
    age = make_attr(NumberAttribute, "age")

    # WHEN we try to create Or with one condition
    # THEN ValueError should be raised
    with pytest.raises(ValueError, match="at least 2"):
        Or(age > 18)
