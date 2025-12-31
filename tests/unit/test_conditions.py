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
    name = make_attr(StringAttribute, "name")
    cond = name == "John"

    names: dict = {}
    values: dict = {}
    result = cond.serialize(names, values)

    assert result == "#n0 = :v0"
    assert names == {"name": "#n0"}
    assert values == {":v0": "John"}


def test_ne():
    status = make_attr(StringAttribute, "status")
    cond = status != "deleted"

    names: dict = {}
    values: dict = {}
    result = cond.serialize(names, values)

    assert result == "#n0 <> :v0"


def test_gt():
    age = make_attr(NumberAttribute, "age")
    cond = age > 18

    names: dict = {}
    values: dict = {}
    result = cond.serialize(names, values)

    assert result == "#n0 > :v0"
    assert values == {":v0": 18}


def test_ge():
    age = make_attr(NumberAttribute, "age")
    cond = age >= 21

    names: dict = {}
    values: dict = {}
    result = cond.serialize(names, values)

    assert result == "#n0 >= :v0"


def test_lt():
    price = make_attr(NumberAttribute, "price")
    cond = price < 100

    names: dict = {}
    values: dict = {}
    result = cond.serialize(names, values)

    assert result == "#n0 < :v0"


def test_le():
    price = make_attr(NumberAttribute, "price")
    cond = price <= 50

    names: dict = {}
    values: dict = {}
    result = cond.serialize(names, values)

    assert result == "#n0 <= :v0"


# Function conditions


def test_exists():
    email = make_attr(StringAttribute, "email")
    cond = email.exists()

    names: dict = {}
    values: dict = {}
    result = cond.serialize(names, values)

    assert result == "attribute_exists(#n0)"
    assert names == {"email": "#n0"}


def test_does_not_exist():
    deleted = make_attr(StringAttribute, "deleted_at")
    cond = deleted.does_not_exist()

    names: dict = {}
    values: dict = {}
    result = cond.serialize(names, values)

    assert result == "attribute_not_exists(#n0)"


def test_begins_with():
    sk = make_attr(StringAttribute, "sk")
    cond = sk.begins_with("ORDER#")

    names: dict = {}
    values: dict = {}
    result = cond.serialize(names, values)

    assert result == "begins_with(#n0, :v0)"
    assert values == {":v0": "ORDER#"}


def test_contains():
    tags = make_attr(ListAttribute, "tags")
    cond = tags.contains("premium")

    names: dict = {}
    values: dict = {}
    result = cond.serialize(names, values)

    assert result == "contains(#n0, :v0)"


def test_between():
    age = make_attr(NumberAttribute, "age")
    cond = age.between(18, 65)

    names: dict = {}
    values: dict = {}
    result = cond.serialize(names, values)

    assert result == "#n0 BETWEEN :v0 AND :v1"
    assert values == {":v0": 18, ":v1": 65}


def test_is_in():
    status = make_attr(StringAttribute, "status")
    cond = status.is_in("active", "pending", "review")

    names: dict = {}
    values: dict = {}
    result = cond.serialize(names, values)

    assert result == "#n0 IN (:v0, :v1, :v2)"
    assert values == {":v0": "active", ":v1": "pending", ":v2": "review"}


# Combined conditions


def test_and_operator():
    age = make_attr(NumberAttribute, "age")
    status = make_attr(StringAttribute, "status")
    cond = (age > 18) & (status == "active")

    names: dict = {}
    values: dict = {}
    result = cond.serialize(names, values)

    assert result == "(#n0 > :v0 AND #n1 = :v1)"
    assert names == {"age": "#n0", "status": "#n1"}


def test_or_operator():
    status = make_attr(StringAttribute, "status")
    cond = (status == "active") | (status == "pending")

    names: dict = {}
    values: dict = {}
    result = cond.serialize(names, values)

    assert result == "(#n0 = :v0 OR #n0 = :v1)"


def test_not_operator():
    deleted = make_attr(StringAttribute, "deleted")
    cond = ~deleted.exists()

    names: dict = {}
    values: dict = {}
    result = cond.serialize(names, values)

    assert result == "(NOT attribute_exists(#n0))"


def test_complex_combination():
    age = make_attr(NumberAttribute, "age")
    status = make_attr(StringAttribute, "status")
    deleted = make_attr(StringAttribute, "deleted")

    cond = ((age > 18) & (status == "active")) | ~deleted.exists()

    names: dict = {}
    values: dict = {}
    result = cond.serialize(names, values)

    assert result == "((#n0 > :v0 AND #n1 = :v1) OR (NOT attribute_exists(#n2)))"


# Nested access


def test_map_access():
    address = make_attr(MapAttribute, "address")
    cond = address["city"] == "NYC"

    names: dict = {}
    values: dict = {}
    result = cond.serialize(names, values)

    assert result == "#n0.#n1 = :v0"
    assert names == {"address": "#n0", "city": "#n1"}


def test_list_access():
    tags = make_attr(ListAttribute, "tags")
    cond = tags[0] == "premium"

    names: dict = {}
    values: dict = {}
    result = cond.serialize(names, values)

    assert result == "#n0[0] = :v0"


def test_deep_nested():
    data = make_attr(MapAttribute, "data")
    cond = data["users"][0]["name"] == "John"

    names: dict = {}
    values: dict = {}
    result = cond.serialize(names, values)

    assert result == "#n0.#n1[0].#n2 = :v0"


# And, Or, Not functions


def test_and_function():
    age = make_attr(NumberAttribute, "age")
    status = make_attr(StringAttribute, "status")
    active = make_attr(StringAttribute, "active")

    cond = And(age > 18, status == "active", active == True)  # noqa: E712

    names: dict = {}
    values: dict = {}
    result = cond.serialize(names, values)

    assert result == "((#n0 > :v0 AND #n1 = :v1) AND #n2 = :v2)"


def test_or_function():
    status = make_attr(StringAttribute, "status")

    cond = Or(status == "a", status == "b", status == "c")

    names: dict = {}
    values: dict = {}
    result = cond.serialize(names, values)

    assert result == "((#n0 = :v0 OR #n0 = :v1) OR #n0 = :v2)"


def test_not_function():
    deleted = make_attr(StringAttribute, "deleted")

    cond = Not(deleted.exists())

    names: dict = {}
    values: dict = {}
    result = cond.serialize(names, values)

    assert result == "(NOT attribute_exists(#n0))"


def test_and_requires_two_conditions():
    age = make_attr(NumberAttribute, "age")

    with pytest.raises(ValueError, match="at least 2"):
        And(age > 18)


def test_or_requires_two_conditions():
    age = make_attr(NumberAttribute, "age")

    with pytest.raises(ValueError, match="at least 2"):
        Or(age > 18)
