"""Unit tests for LocalSecondaryIndex."""

from __future__ import annotations

from typing import Any

import pytest
from pydynox import Model, ModelConfig
from pydynox.attributes import NumberAttribute, StringAttribute
from pydynox.indexes import GlobalSecondaryIndex, LocalSecondaryIndex


class User(Model):
    """Test model with LSIs."""

    model_config = ModelConfig(table="users")

    pk = StringAttribute(partition_key=True)
    sk = StringAttribute(sort_key=True)
    email = StringAttribute()
    status = StringAttribute()
    age = NumberAttribute()
    created_at = StringAttribute()

    # GSI for comparison
    email_index = GlobalSecondaryIndex(
        index_name="email-index",
        partition_key="email",
    )

    # LSI with status as alternate sort key
    status_index = LocalSecondaryIndex(
        index_name="status-index",
        sort_key="status",
    )

    # LSI with custom projection
    age_index = LocalSecondaryIndex(
        index_name="age-index",
        sort_key="age",
        projection=["email", "status"],
    )

    # LSI with KEYS_ONLY projection
    created_index = LocalSecondaryIndex(
        index_name="created-index",
        sort_key="created_at",
        projection="KEYS_ONLY",
    )


def test_lsi_definition() -> None:
    """LSI is defined correctly on model."""
    # GIVEN a model with LSI defined

    # THEN LSI should be accessible and have correct config
    assert hasattr(User, "status_index")
    assert User.status_index.index_name == "status-index"
    assert User.status_index.sort_key == "status"


def test_lsi_collected_in_model() -> None:
    """LSIs are collected in model._local_indexes."""
    # GIVEN a model with multiple LSIs

    # THEN LSIs should be in _local_indexes dict
    assert "status_index" in User._local_indexes
    assert "age_index" in User._local_indexes
    assert "created_index" in User._local_indexes
    assert User._local_indexes["status_index"] is User.status_index


def test_lsi_bound_to_model() -> None:
    """LSI is bound to model class."""
    # GIVEN LSIs on a model

    # THEN they should be bound to the model class
    assert User.status_index._model_class is User
    assert User.age_index._model_class is User


def test_lsi_to_create_table_definition_all_projection() -> None:
    """LSI converts to create_table format with ALL projection."""
    # GIVEN an LSI with default ALL projection

    # WHEN we convert to create_table definition
    definition = User.status_index.to_create_table_definition(User)

    # THEN it should have correct format (Rust expects range_key)
    assert definition["index_name"] == "status-index"
    assert definition["range_key"] == ("status", "S")
    assert definition["projection"] == "ALL"


def test_lsi_to_create_table_definition_custom_projection() -> None:
    """LSI converts to create_table format with custom projection."""
    # GIVEN an LSI with INCLUDE projection

    # WHEN we convert to create_table definition
    definition = User.age_index.to_create_table_definition(User)

    # THEN projection should be INCLUDE with specified attributes (Rust expects range_key)
    assert definition["index_name"] == "age-index"
    assert definition["range_key"] == ("age", "N")
    assert definition["projection"] == "INCLUDE"
    assert definition["non_key_attributes"] == ["email", "status"]


def test_lsi_to_create_table_definition_keys_only() -> None:
    """LSI converts to create_table format with KEYS_ONLY projection."""
    # GIVEN an LSI with KEYS_ONLY projection

    # WHEN we convert to create_table definition
    definition = User.created_index.to_create_table_definition(User)

    # THEN projection should be KEYS_ONLY (Rust expects range_key)
    assert definition["index_name"] == "created-index"
    assert definition["range_key"] == ("created_at", "S")
    assert definition["projection"] == "KEYS_ONLY"


def test_lsi_query_requires_partition_key() -> None:
    """LSI query raises error if hash key not provided."""
    # GIVEN an LSI that requires the table's hash key

    # WHEN we query without the hash key
    # THEN ValueError should be raised
    with pytest.raises(ValueError, match="requires the table's hash key 'pk'"):
        User.status_index.query(status="active")


def test_lsi_unbound_raises_error() -> None:
    """Unbound LSI raises error on query."""
    # GIVEN an unbound LSI
    unbound_lsi: LocalSecondaryIndex[Any] = LocalSecondaryIndex(
        index_name="test",
        sort_key="test",
    )

    # WHEN we try to query
    # THEN RuntimeError should be raised
    with pytest.raises(RuntimeError, match="not bound to a model"):
        unbound_lsi.query(pk="USER#1")


def test_lsi_inheritance() -> None:
    """LSIs are inherited from parent class."""

    # GIVEN a child class that inherits from User
    class AdminUser(User):
        role = StringAttribute()

    # THEN LSIs should be inherited and bound to child
    assert "status_index" in AdminUser._local_indexes
    assert "age_index" in AdminUser._local_indexes
    assert AdminUser.status_index._model_class is AdminUser


def test_lsi_invalid_sort_key() -> None:
    """LSI raises error for invalid range key attribute."""

    # GIVEN a model with LSI referencing nonexistent attribute
    class BadModel(Model):
        model_config = ModelConfig(table="bad")
        pk = StringAttribute(partition_key=True)
        sk = StringAttribute(sort_key=True)

        bad_index = LocalSecondaryIndex(
            index_name="bad-index",
            sort_key="nonexistent",
        )

    # WHEN we try to convert to create_table definition
    # THEN ValueError should be raised
    with pytest.raises(ValueError, match="references attribute 'nonexistent'"):
        BadModel.bad_index.to_create_table_definition(BadModel)


def test_gsi_and_lsi_coexist() -> None:
    """GSIs and LSIs can coexist on the same model."""
    # GIVEN a model with both GSI and LSI

    # THEN GSIs should be in _indexes
    assert "email_index" in User._indexes
    assert "email_index" not in User._local_indexes

    # AND LSIs should be in _local_indexes
    assert "status_index" in User._local_indexes
    assert "status_index" not in User._indexes
