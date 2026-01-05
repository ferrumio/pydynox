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

    pk = StringAttribute(hash_key=True)
    sk = StringAttribute(range_key=True)
    email = StringAttribute()
    status = StringAttribute()
    age = NumberAttribute()
    tenant_id = StringAttribute()
    region = StringAttribute()
    created_at = StringAttribute()
    item_id = StringAttribute()

    email_index = GlobalSecondaryIndex(
        index_name="email-index",
        hash_key="email",
    )

    status_index = GlobalSecondaryIndex(
        index_name="status-index",
        hash_key="status",
        range_key="pk",
    )

    custom_projection_index = GlobalSecondaryIndex(
        index_name="custom-index",
        hash_key="status",
        projection=["email", "age"],
    )

    keys_only_index = GlobalSecondaryIndex(
        index_name="keys-only-index",
        hash_key="email",
        projection="KEYS_ONLY",
    )

    # Multi-attribute GSI (new in Nov 2025)
    location_index = GlobalSecondaryIndex(
        index_name="location-index",
        hash_key=["tenant_id", "region"],
        range_key=["created_at", "item_id"],
    )


def test_gsi_definition() -> None:
    """Test GSI is defined correctly on model."""
    assert hasattr(User, "email_index")
    assert hasattr(User, "status_index")
    assert User.email_index.index_name == "email-index"
    assert User.email_index.hash_key == "email"
    assert User.email_index.range_key is None


def test_gsi_with_range_key() -> None:
    """Test GSI with range key."""
    assert User.status_index.index_name == "status-index"
    assert User.status_index.hash_key == "status"
    assert User.status_index.range_key == "pk"


def test_gsi_collected_in_model() -> None:
    """Test GSIs are collected in model._indexes."""
    assert "email_index" in User._indexes
    assert "status_index" in User._indexes
    assert User._indexes["email_index"] is User.email_index


def test_gsi_bound_to_model() -> None:
    """Test GSI is bound to model class."""
    assert User.email_index._model_class is User
    assert User.status_index._model_class is User


def test_gsi_to_dynamodb_definition_all_projection() -> None:
    """Test GSI converts to DynamoDB format with ALL projection."""
    definition = User.email_index.to_dynamodb_definition()

    assert definition["IndexName"] == "email-index"
    assert definition["KeySchema"] == [{"AttributeName": "email", "KeyType": "HASH"}]
    assert definition["Projection"] == {"ProjectionType": "ALL"}


def test_gsi_to_dynamodb_definition_with_range_key() -> None:
    """Test GSI converts to DynamoDB format with range key."""
    definition = User.status_index.to_dynamodb_definition()

    assert definition["IndexName"] == "status-index"
    assert definition["KeySchema"] == [
        {"AttributeName": "status", "KeyType": "HASH"},
        {"AttributeName": "pk", "KeyType": "RANGE"},
    ]


def test_gsi_to_dynamodb_definition_custom_projection() -> None:
    """Test GSI converts to DynamoDB format with custom projection."""
    definition = User.custom_projection_index.to_dynamodb_definition()

    assert definition["Projection"] == {
        "ProjectionType": "INCLUDE",
        "NonKeyAttributes": ["email", "age"],
    }


def test_gsi_to_dynamodb_definition_keys_only() -> None:
    """Test GSI converts to DynamoDB format with KEYS_ONLY projection."""
    definition = User.keys_only_index.to_dynamodb_definition()

    assert definition["Projection"] == {"ProjectionType": "KEYS_ONLY"}


def test_gsi_query_requires_hash_key() -> None:
    """Test GSI query raises error if hash key not provided."""
    with pytest.raises(ValueError, match="requires all hash key attributes"):
        User.email_index.query(status="active")  # type: ignore[call-arg]


def test_gsi_unbound_raises_error() -> None:
    """Test unbound GSI raises error on query."""
    unbound_gsi: GlobalSecondaryIndex[Any] = GlobalSecondaryIndex(
        index_name="test",
        hash_key="test",
    )

    with pytest.raises(RuntimeError, match="not bound to a model"):
        unbound_gsi.query(test="value")


def test_gsi_inheritance() -> None:
    """Test GSIs are inherited from parent class."""

    class AdminUser(User):
        role = StringAttribute()

    assert "email_index" in AdminUser._indexes
    assert "status_index" in AdminUser._indexes
    assert AdminUser.email_index._model_class is AdminUser


# ============ Multi-attribute GSI tests ============


def test_multi_attr_gsi_definition() -> None:
    """Test multi-attribute GSI is defined correctly."""
    assert User.location_index.index_name == "location-index"
    assert User.location_index.hash_keys == ["tenant_id", "region"]
    assert User.location_index.range_keys == ["created_at", "item_id"]
    # Backward compat: first attribute accessible via hash_key/range_key
    assert User.location_index.hash_key == "tenant_id"
    assert User.location_index.range_key == "created_at"


def test_multi_attr_gsi_to_dynamodb_definition() -> None:
    """Test multi-attribute GSI converts to DynamoDB format."""
    definition = User.location_index.to_dynamodb_definition()

    assert definition["IndexName"] == "location-index"
    assert definition["KeySchema"] == [
        {"AttributeName": "tenant_id", "KeyType": "HASH"},
        {"AttributeName": "region", "KeyType": "HASH"},
        {"AttributeName": "created_at", "KeyType": "RANGE"},
        {"AttributeName": "item_id", "KeyType": "RANGE"},
    ]


def test_multi_attr_gsi_query_requires_all_hash_keys() -> None:
    """Test multi-attribute GSI query requires all hash key attributes."""
    # Missing region
    with pytest.raises(ValueError, match="Missing: \\['region'\\]"):
        User.location_index.query(tenant_id="ACME")

    # Missing tenant_id
    with pytest.raises(ValueError, match="Missing: \\['tenant_id'\\]"):
        User.location_index.query(region="us-east-1")


def test_multi_attr_gsi_validation_max_4_hash_keys() -> None:
    """Test GSI rejects more than 4 hash key attributes."""
    with pytest.raises(ValueError, match="at most 4 attributes"):
        GlobalSecondaryIndex(
            index_name="too-many-hash",
            hash_key=["a", "b", "c", "d", "e"],  # 5 attributes
        )


def test_multi_attr_gsi_validation_max_4_range_keys() -> None:
    """Test GSI rejects more than 4 range key attributes."""
    with pytest.raises(ValueError, match="at most 4 attributes"):
        GlobalSecondaryIndex(
            index_name="too-many-range",
            hash_key="pk",
            range_key=["a", "b", "c", "d", "e"],  # 5 attributes
        )


def test_multi_attr_gsi_validation_empty_hash_key() -> None:
    """Test GSI rejects empty hash key."""
    with pytest.raises(ValueError, match="hash_key is required"):
        GlobalSecondaryIndex(
            index_name="empty-hash",
            hash_key=[],  # type: ignore[arg-type]
        )


def test_single_attr_gsi_backward_compat() -> None:
    """Test single-attribute GSI still works (backward compat)."""
    gsi = GlobalSecondaryIndex(
        index_name="test",
        hash_key="email",
        range_key="created_at",
    )
    # Should be normalized to lists internally
    assert gsi.hash_keys == ["email"]
    assert gsi.range_keys == ["created_at"]
    # But still accessible via old properties
    assert gsi.hash_key == "email"
    assert gsi.range_key == "created_at"
