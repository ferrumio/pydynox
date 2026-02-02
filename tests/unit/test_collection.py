"""Unit tests for Collection."""

from __future__ import annotations

import pytest
from pydynox import Collection, CollectionResult, Model, ModelConfig
from pydynox.attributes import StringAttribute


# Test models
class BaseEntity(Model):
    model_config = ModelConfig(table="test_table")
    pk = StringAttribute(partition_key=True)
    sk = StringAttribute(sort_key=True)
    _type = StringAttribute(discriminator=True)


class User(BaseEntity):
    name = StringAttribute()


class Order(BaseEntity):
    total = StringAttribute()


class Address(BaseEntity):
    city = StringAttribute()


# Model without discriminator
class NoDiscriminator(Model):
    model_config = ModelConfig(table="test_table")
    pk = StringAttribute(partition_key=True)


# Model with different table
class DifferentTable(Model):
    model_config = ModelConfig(table="other_table")
    pk = StringAttribute(partition_key=True)
    _type = StringAttribute(discriminator=True)


def test_collection_init():
    collection = Collection([User, Order, Address])
    assert len(collection._models) == 3


def test_collection_empty_raises():
    with pytest.raises(ValueError, match="requires at least one model"):
        Collection([])


def test_collection_no_discriminator_raises():
    with pytest.raises(ValueError, match="no discriminator field"):
        Collection([NoDiscriminator])


def test_collection_different_tables_raises():
    with pytest.raises(ValueError, match="must share the same table"):
        Collection([User, DifferentTable])


def test_collection_result_get():
    items = [
        {"pk": "USER#1", "sk": "PROFILE", "_type": "User", "name": "John"},
        {"pk": "USER#1", "sk": "ORDER#1", "_type": "Order", "total": "100"},
        {"pk": "USER#1", "sk": "ORDER#2", "_type": "Order", "total": "200"},
    ]
    result = CollectionResult([User, Order], items)

    users = result.get(User)
    assert len(users) == 1
    assert isinstance(users[0], User)
    assert users[0].name == "John"

    orders = result.get(Order)
    assert len(orders) == 2
    assert all(isinstance(o, Order) for o in orders)


def test_collection_result_attribute_access():
    items = [
        {"pk": "USER#1", "sk": "PROFILE", "_type": "User", "name": "John"},
        {"pk": "USER#1", "sk": "ORDER#1", "_type": "Order", "total": "100"},
    ]
    result = CollectionResult([User, Order], items)

    # Access via pluralized name
    assert len(result.users) == 1
    assert len(result.orders) == 1


def test_collection_result_unknown_attribute_raises():
    items = []
    result = CollectionResult([User], items)

    with pytest.raises(AttributeError, match="has no attribute"):
        _ = result.unknown


def test_collection_result_repr():
    items = [
        {"pk": "USER#1", "sk": "PROFILE", "_type": "User", "name": "John"},
        {"pk": "USER#1", "sk": "ORDER#1", "_type": "Order", "total": "100"},
    ]
    result = CollectionResult([User, Order], items)

    repr_str = repr(result)
    assert "User: 1" in repr_str
    assert "Order: 1" in repr_str


def test_collection_repr():
    collection = Collection([User, Order])
    repr_str = repr(collection)
    assert "User" in repr_str
    assert "Order" in repr_str


def test_collection_result_empty():
    result = CollectionResult([User, Order], [])

    assert result.get(User) == []
    assert result.get(Order) == []
    assert result.users == []
    assert result.orders == []


def test_collection_result_ignores_unknown_types():
    items = [
        {"pk": "USER#1", "sk": "PROFILE", "_type": "Unknown", "name": "John"},
    ]
    result = CollectionResult([User, Order], items)

    # Unknown type is ignored
    assert result.get(User) == []
    assert result.get(Order) == []


def test_collection_get_table():
    collection = Collection([User, Order])
    assert collection._get_table() == "test_table"


# Template resolution tests
class TemplateModel(Model):
    model_config = ModelConfig(table="test_table")
    pk = StringAttribute(partition_key=True, template="USER#{user_id}")
    sk = StringAttribute(sort_key=True)
    _type = StringAttribute(discriminator=True)
    user_id = StringAttribute()


def test_collection_resolve_pk_from_template():
    collection = Collection([TemplateModel])
    pk = collection._resolve_pk_from_template({"user_id": "123"})
    assert pk == "USER#123"


def test_collection_resolve_pk_missing_placeholder():
    collection = Collection([TemplateModel])
    pk = collection._resolve_pk_from_template({"other": "value"})
    assert pk is None


def test_collection_resolve_pk_no_template():
    collection = Collection([User])
    pk = collection._resolve_pk_from_template({"user_id": "123"})
    assert pk is None
