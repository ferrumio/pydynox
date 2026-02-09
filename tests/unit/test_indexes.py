"""Unit tests for GlobalSecondaryIndex."""

from __future__ import annotations

from typing import Any

import pytest
from pydynox import Model, ModelConfig
from pydynox.attributes import NumberAttribute, StringAttribute
from pydynox.indexes import GlobalSecondaryIndex


class User(Model):
    """Test model with GSIs."""

    model_config = ModelConfig(table="users")

    pk = StringAttribute(partition_key=True)
    sk = StringAttribute(sort_key=True)
    email = StringAttribute()
    status = StringAttribute()
    age = NumberAttribute()
    tenant_id = StringAttribute()
    region = StringAttribute()
    created_at = StringAttribute()
    item_id = StringAttribute()

    email_index = GlobalSecondaryIndex(
        index_name="email-index",
        partition_key="email",
    )

    status_index = GlobalSecondaryIndex(
        index_name="status-index",
        partition_key="status",
        sort_key="pk",
    )

    custom_projection_index = GlobalSecondaryIndex(
        index_name="custom-index",
        partition_key="status",
        projection=["email", "age"],
    )

    keys_only_index = GlobalSecondaryIndex(
        index_name="keys-only-index",
        partition_key="email",
        projection="KEYS_ONLY",
    )

    # Multi-attribute GSI (new in Nov 2025)
    location_index = GlobalSecondaryIndex(
        index_name="location-index",
        partition_key=["tenant_id", "region"],
        sort_key=["created_at", "item_id"],
    )


def test_gsi_definition() -> None:
    """Test GSI is defined correctly on model."""
    # GIVEN a model with GSIs defined

    # THEN GSIs should be accessible and have correct config
    assert hasattr(User, "email_index")
    assert hasattr(User, "status_index")
    assert User.email_index.index_name == "email-index"
    assert User.email_index.partition_key == "email"
    assert User.email_index.sort_key is None


def test_gsi_with_sort_key() -> None:
    """Test GSI with range key."""
    # GIVEN a GSI with range key

    # THEN both hash and range key should be set
    assert User.status_index.index_name == "status-index"
    assert User.status_index.partition_key == "status"
    assert User.status_index.sort_key == "pk"


def test_gsi_collected_in_model() -> None:
    """Test GSIs are collected in model._indexes."""
    # GIVEN a model with GSIs

    # THEN GSIs should be in _indexes dict
    assert "email_index" in User._indexes
    assert "status_index" in User._indexes
    assert User._indexes["email_index"] is User.email_index


def test_gsi_bound_to_model() -> None:
    """Test GSI is bound to model class."""
    # GIVEN GSIs on a model

    # THEN they should be bound to the model class
    assert User.email_index._model_class is User
    assert User.status_index._model_class is User


def test_gsi_to_dynamodb_definition_all_projection() -> None:
    """Test GSI converts to DynamoDB format with ALL projection."""
    # GIVEN a GSI with default ALL projection

    # WHEN we convert to DynamoDB definition
    definition = User.email_index.to_dynamodb_definition()

    # THEN it should have correct format
    assert definition["IndexName"] == "email-index"
    assert definition["KeySchema"] == [{"AttributeName": "email", "KeyType": "HASH"}]
    assert definition["Projection"] == {"ProjectionType": "ALL"}


def test_gsi_to_dynamodb_definition_with_sort_key() -> None:
    """Test GSI converts to DynamoDB format with range key."""
    # GIVEN a GSI with range key

    # WHEN we convert to DynamoDB definition
    definition = User.status_index.to_dynamodb_definition()

    # THEN KeySchema should include both hash and range
    assert definition["IndexName"] == "status-index"
    assert definition["KeySchema"] == [
        {"AttributeName": "status", "KeyType": "HASH"},
        {"AttributeName": "pk", "KeyType": "RANGE"},
    ]


def test_gsi_to_dynamodb_definition_custom_projection() -> None:
    """Test GSI converts to DynamoDB format with custom projection."""
    # GIVEN a GSI with custom projection

    # WHEN we convert to DynamoDB definition
    definition = User.custom_projection_index.to_dynamodb_definition()

    # THEN projection should be INCLUDE with specified attributes
    assert definition["Projection"] == {
        "ProjectionType": "INCLUDE",
        "NonKeyAttributes": ["email", "age"],
    }


def test_gsi_to_dynamodb_definition_keys_only() -> None:
    """Test GSI converts to DynamoDB format with KEYS_ONLY projection."""
    # GIVEN a GSI with KEYS_ONLY projection

    # WHEN we convert to DynamoDB definition
    definition = User.keys_only_index.to_dynamodb_definition()

    # THEN projection should be KEYS_ONLY
    assert definition["Projection"] == {"ProjectionType": "KEYS_ONLY"}


def test_gsi_query_requires_partition_key() -> None:
    """Test GSI query raises error if hash key not provided."""
    # GIVEN a GSI that requires email as hash key

    # WHEN we query without the hash key
    # THEN ValueError should be raised
    with pytest.raises(ValueError, match="requires a partition key value"):
        User.email_index.query(status="active")  # type: ignore[call-arg]


def test_gsi_unbound_raises_error() -> None:
    """Test unbound GSI raises error on query."""
    # GIVEN an unbound GSI
    unbound_gsi: GlobalSecondaryIndex[Any] = GlobalSecondaryIndex(
        index_name="test",
        partition_key="test",
    )

    # WHEN we try to query
    # THEN RuntimeError should be raised
    with pytest.raises(RuntimeError, match="not bound to a model"):
        unbound_gsi.query(test="value")


def test_gsi_inheritance() -> None:
    """Test GSIs are inherited from parent class."""

    # GIVEN a child class that inherits from User
    class AdminUser(User):
        role = StringAttribute()

    # THEN GSIs should be inherited and bound to child
    assert "email_index" in AdminUser._indexes
    assert "status_index" in AdminUser._indexes
    assert AdminUser.email_index._model_class is AdminUser


# ============ Multi-attribute GSI tests ============


def test_multi_attr_gsi_definition() -> None:
    """Test multi-attribute GSI is defined correctly."""
    # GIVEN a multi-attribute GSI

    # THEN it should have multiple hash and range keys
    assert User.location_index.index_name == "location-index"
    assert User.location_index.partition_keys == ["tenant_id", "region"]
    assert User.location_index.sort_keys == ["created_at", "item_id"]
    # Backward compat: first attribute accessible via partition_key/sort_key
    assert User.location_index.partition_key == "tenant_id"
    assert User.location_index.sort_key == "created_at"


def test_multi_attr_gsi_to_dynamodb_definition() -> None:
    """Test multi-attribute GSI converts to DynamoDB format."""
    # GIVEN a multi-attribute GSI

    # WHEN we convert to DynamoDB definition
    definition = User.location_index.to_dynamodb_definition()

    # THEN KeySchema should include all attributes
    assert definition["IndexName"] == "location-index"
    assert definition["KeySchema"] == [
        {"AttributeName": "tenant_id", "KeyType": "HASH"},
        {"AttributeName": "region", "KeyType": "HASH"},
        {"AttributeName": "created_at", "KeyType": "RANGE"},
        {"AttributeName": "item_id", "KeyType": "RANGE"},
    ]


def test_multi_attr_gsi_query_requires_all_partition_keys() -> None:
    """Test multi-attribute GSI query requires all hash key attributes."""
    # GIVEN a multi-attribute GSI requiring tenant_id and region

    # WHEN we query with missing region
    # THEN ValueError should be raised
    with pytest.raises(ValueError, match="requires 'region'"):
        User.location_index.query(tenant_id="ACME")

    # WHEN we query with missing tenant_id
    # THEN ValueError should be raised
    with pytest.raises(ValueError, match="requires 'tenant_id'"):
        User.location_index.query(region="us-east-1")


def test_multi_attr_gsi_validation_max_4_partition_keys() -> None:
    """Test GSI rejects more than 4 hash key attributes."""
    # WHEN we try to create a GSI with 5 hash keys
    # THEN ValueError should be raised
    with pytest.raises(ValueError, match="at most 4 attributes"):
        GlobalSecondaryIndex(
            index_name="too-many-hash",
            partition_key=["a", "b", "c", "d", "e"],  # 5 attributes
        )


def test_multi_attr_gsi_validation_max_4_sort_keys() -> None:
    """Test GSI rejects more than 4 range key attributes."""
    # WHEN we try to create a GSI with 5 range keys
    # THEN ValueError should be raised
    with pytest.raises(ValueError, match="at most 4 attributes"):
        GlobalSecondaryIndex(
            index_name="too-many-range",
            partition_key="pk",
            sort_key=["a", "b", "c", "d", "e"],  # 5 attributes
        )


def test_multi_attr_gsi_validation_empty_partition_key() -> None:
    """Test GSI rejects empty hash key."""
    # WHEN we try to create a GSI with empty hash key
    # THEN ValueError should be raised
    with pytest.raises(ValueError, match="partition_key is required"):
        GlobalSecondaryIndex(
            index_name="empty-hash",
            partition_key=[],  # type: ignore[arg-type]
        )


def test_single_attr_gsi_backward_compat() -> None:
    """Test single-attribute GSI still works (backward compat)."""
    # GIVEN a single-attribute GSI
    gsi = GlobalSecondaryIndex(
        index_name="test",
        partition_key="email",
        sort_key="created_at",
    )

    # THEN it should be normalized to lists internally
    assert gsi.partition_keys == ["email"]
    assert gsi.sort_keys == ["created_at"]

    # AND still accessible via old properties
    assert gsi.partition_key == "email"
    assert gsi.sort_key == "created_at"


# ============ partition_key= unified API tests ============


def test_gsi_query_with_partition_key_kwarg() -> None:
    """GSI query accepts partition_key= for single-attribute GSI."""
    # GIVEN a single-attribute GSI (email_index)

    # WHEN we query using partition_key=
    result = User.email_index.query(partition_key="john@example.com")

    # THEN it should resolve correctly
    assert result._partition_key_values == {"email": "john@example.com"}


def test_gsi_sync_query_with_partition_key_kwarg() -> None:
    """GSI sync_query accepts partition_key= for single-attribute GSI."""
    result = User.email_index.sync_query(partition_key="john@example.com")
    assert result._partition_key_values == {"email": "john@example.com"}


def test_gsi_query_with_attribute_name_still_works() -> None:
    """GSI query still accepts attribute name as kwarg (backward compat)."""
    result = User.email_index.query(email="john@example.com")
    assert result._partition_key_values == {"email": "john@example.com"}


def test_gsi_sync_query_with_attribute_name_still_works() -> None:
    """GSI sync_query still accepts attribute name as kwarg (backward compat)."""
    result = User.email_index.sync_query(email="john@example.com")
    assert result._partition_key_values == {"email": "john@example.com"}


def test_gsi_partition_key_rejects_multi_attr() -> None:
    """partition_key= raises error for multi-attribute GSI."""
    # GIVEN a multi-attribute GSI (location_index with tenant_id + region)

    # WHEN we try to use partition_key= on it
    # THEN ValueError should be raised with helpful message
    with pytest.raises(ValueError, match="composite partition key"):
        User.location_index.query(partition_key="ACME")


def test_gsi_partition_key_rejects_multi_attr_sync() -> None:
    """partition_key= raises error for multi-attribute GSI (sync)."""
    with pytest.raises(ValueError, match="composite partition key"):
        User.location_index.sync_query(partition_key="ACME")


def test_multi_attr_gsi_query_with_kwargs_still_works() -> None:
    """Multi-attribute GSI still works with kwargs."""
    result = User.location_index.query(tenant_id="ACME", region="us-east-1")
    assert result._partition_key_values == {"tenant_id": "ACME", "region": "us-east-1"}
