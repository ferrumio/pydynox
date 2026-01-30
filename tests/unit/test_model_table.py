"""Unit tests for Model table operations (sync_create_table, sync_table_exists, sync_delete_table).

Tests the sync versions of table operations. Async versions are tested in integration tests.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from pydynox import DynamoDBClient, Model, ModelConfig
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

    email_index = GlobalSecondaryIndex(
        index_name="email-index",
        partition_key="email",
    )

    status_age_index = GlobalSecondaryIndex(
        index_name="status-age-index",
        partition_key="status",
        sort_key="age",
    )

    location_index = GlobalSecondaryIndex(
        index_name="location-index",
        partition_key=["tenant_id", "region"],
    )


class SimpleModel(Model):
    """Model with only hash key."""

    model_config = ModelConfig(table="simple")
    pk = StringAttribute(partition_key=True)
    name = StringAttribute()


class NoKeyModel(Model):
    """Model without hash key (invalid)."""

    model_config = ModelConfig(table="nokey")
    name = StringAttribute()


@pytest.fixture
def mock_client() -> MagicMock:
    """Create a mock DynamoDB client."""
    client = MagicMock(spec=DynamoDBClient)
    return client


def test_sync_create_table_basic(mock_client: MagicMock) -> None:
    """Test sync_create_table with basic model."""
    # GIVEN a simple model with mock client
    with patch.object(SimpleModel, "_get_client", return_value=mock_client):
        # WHEN we create the table
        SimpleModel.sync_create_table()

    # THEN sync_create_table should be called with correct params
    mock_client.sync_create_table.assert_called_once_with(
        "simple",
        partition_key=("pk", "S"),
        sort_key=None,
        billing_mode="PAY_PER_REQUEST",
        read_capacity=None,
        write_capacity=None,
        table_class=None,
        encryption=None,
        kms_key_id=None,
        global_secondary_indexes=None,
        local_secondary_indexes=None,
        wait=False,
    )


def test_sync_create_table_with_sort_key(mock_client: MagicMock) -> None:
    """Test sync_create_table with hash and range key."""

    # GIVEN a model with range key
    class WithRange(Model):
        model_config = ModelConfig(table="with_range")
        pk = StringAttribute(partition_key=True)
        sk = NumberAttribute(sort_key=True)

    with patch.object(WithRange, "_get_client", return_value=mock_client):
        # WHEN we create the table
        WithRange.sync_create_table()

    # THEN both hash and range key should be included
    mock_client.sync_create_table.assert_called_once()
    call_args = mock_client.sync_create_table.call_args
    assert call_args[0][0] == "with_range"
    assert call_args[1]["partition_key"] == ("pk", "S")
    assert call_args[1]["sort_key"] == ("sk", "N")


def test_sync_create_table_with_gsis(mock_client: MagicMock) -> None:
    """Test sync_create_table includes GSI definitions."""
    # GIVEN a model with GSIs
    with patch.object(User, "_get_client", return_value=mock_client):
        # WHEN we create the table
        User.sync_create_table()

    # THEN GSIs should be included
    mock_client.sync_create_table.assert_called_once()
    call_args = mock_client.sync_create_table.call_args

    gsis = call_args[1]["global_secondary_indexes"]
    assert gsis is not None
    assert len(gsis) == 3

    # Find each GSI by name
    gsi_by_name = {g["index_name"]: g for g in gsis}

    # Single-attribute GSI (Rust expects hash_key/range_key)
    email_gsi = gsi_by_name["email-index"]
    assert email_gsi["hash_key"] == ("email", "S")
    assert "range_key" not in email_gsi

    # GSI with range key
    status_gsi = gsi_by_name["status-age-index"]
    assert status_gsi["hash_key"] == ("status", "S")
    assert status_gsi["range_key"] == ("age", "N")

    # Multi-attribute GSI
    location_gsi = gsi_by_name["location-index"]
    assert location_gsi["hash_keys"] == [("tenant_id", "S"), ("region", "S")]


def test_sync_create_table_with_options(mock_client: MagicMock) -> None:
    """Test sync_create_table with all options."""
    # GIVEN a model with mock client
    with patch.object(SimpleModel, "_get_client", return_value=mock_client):
        # WHEN we create the table with all options
        SimpleModel.sync_create_table(
            billing_mode="PROVISIONED",
            read_capacity=10,
            write_capacity=5,
            table_class="STANDARD_INFREQUENT_ACCESS",
            encryption="CUSTOMER_MANAGED",
            kms_key_id="arn:aws:kms:us-east-1:123456789012:key/abc",
            wait=True,
        )

    # THEN all options should be passed
    mock_client.sync_create_table.assert_called_once_with(
        "simple",
        partition_key=("pk", "S"),
        sort_key=None,
        billing_mode="PROVISIONED",
        read_capacity=10,
        write_capacity=5,
        table_class="STANDARD_INFREQUENT_ACCESS",
        encryption="CUSTOMER_MANAGED",
        kms_key_id="arn:aws:kms:us-east-1:123456789012:key/abc",
        global_secondary_indexes=None,
        local_secondary_indexes=None,
        wait=True,
    )


def test_sync_create_table_no_partition_key_raises() -> None:
    """Test sync_create_table raises error if no hash key defined."""
    # GIVEN a model without hash key
    mock_client = MagicMock(spec=DynamoDBClient)

    with patch.object(NoKeyModel, "_get_client", return_value=mock_client):
        # WHEN we try to create the table
        # THEN ValueError should be raised
        with pytest.raises(ValueError, match="has no partition_key defined"):
            NoKeyModel.sync_create_table()


def test_sync_table_exists(mock_client: MagicMock) -> None:
    """Test sync_table_exists calls client correctly."""
    # GIVEN a mock client that returns True
    mock_client.sync_table_exists.return_value = True

    with patch.object(SimpleModel, "_get_client", return_value=mock_client):
        # WHEN we check if table exists
        result = SimpleModel.sync_table_exists()

    # THEN it should return True
    assert result is True
    mock_client.sync_table_exists.assert_called_once_with("simple")


def test_sync_table_exists_false(mock_client: MagicMock) -> None:
    """Test sync_table_exists returns False when table doesn't exist."""
    # GIVEN a mock client that returns False
    mock_client.sync_table_exists.return_value = False

    with patch.object(SimpleModel, "_get_client", return_value=mock_client):
        # WHEN we check if table exists
        result = SimpleModel.sync_table_exists()

    # THEN it should return False
    assert result is False


def test_sync_delete_table(mock_client: MagicMock) -> None:
    """Test sync_delete_table calls client correctly."""
    # GIVEN a model with mock client
    with patch.object(SimpleModel, "_get_client", return_value=mock_client):
        # WHEN we delete the table
        SimpleModel.sync_delete_table()

    # THEN sync_delete_table should be called
    mock_client.sync_delete_table.assert_called_once_with("simple")


def test_gsi_to_create_table_definition_single_attr() -> None:
    """Test GSI to_create_table_definition with single attribute keys."""
    # GIVEN a GSI with single attribute hash key

    # WHEN we get the definition
    definition = User.email_index.to_create_table_definition(User)

    # THEN it should have correct format (Rust expects hash_key/range_key)
    assert definition["index_name"] == "email-index"
    assert definition["hash_key"] == ("email", "S")
    assert "range_key" not in definition
    assert definition["projection"] == "ALL"


def test_gsi_to_create_table_definition_with_range() -> None:
    """Test GSI to_create_table_definition with range key."""
    # GIVEN a GSI with range key

    # WHEN we get the definition
    definition = User.status_age_index.to_create_table_definition(User)

    # THEN it should include range key (Rust expects hash_key/range_key)
    assert definition["index_name"] == "status-age-index"
    assert definition["hash_key"] == ("status", "S")
    assert definition["range_key"] == ("age", "N")


def test_gsi_to_create_table_definition_multi_attr() -> None:
    """Test GSI to_create_table_definition with multi-attribute keys."""
    # GIVEN a multi-attribute GSI

    # WHEN we get the definition
    definition = User.location_index.to_create_table_definition(User)

    # THEN it should use hash_keys (plural, Rust expects this)
    assert definition["index_name"] == "location-index"
    assert definition["hash_keys"] == [("tenant_id", "S"), ("region", "S")]
    assert "hash_key" not in definition


def test_gsi_to_create_table_definition_keys_only_projection() -> None:
    """Test GSI to_create_table_definition with KEYS_ONLY projection."""

    # GIVEN a model with KEYS_ONLY projection GSI
    class ModelWithKeysOnly(Model):
        model_config = ModelConfig(table="test")
        pk = StringAttribute(partition_key=True)
        email = StringAttribute()

        email_index = GlobalSecondaryIndex(
            index_name="email-index",
            partition_key="email",
            projection="KEYS_ONLY",
        )

    # WHEN we get the definition
    definition = ModelWithKeysOnly.email_index.to_create_table_definition(ModelWithKeysOnly)

    # THEN projection should be KEYS_ONLY
    assert definition["projection"] == "KEYS_ONLY"


def test_gsi_to_create_table_definition_include_projection() -> None:
    """Test GSI to_create_table_definition with INCLUDE projection."""

    # GIVEN a model with INCLUDE projection GSI
    class ModelWithInclude(Model):
        model_config = ModelConfig(table="test")
        pk = StringAttribute(partition_key=True)
        email = StringAttribute()
        name = StringAttribute()
        age = NumberAttribute()

        email_index = GlobalSecondaryIndex(
            index_name="email-index",
            partition_key="email",
            projection=["name", "age"],
        )

    # WHEN we get the definition
    definition = ModelWithInclude.email_index.to_create_table_definition(ModelWithInclude)

    # THEN projection should be INCLUDE with non_key_attributes
    assert definition["projection"] == "INCLUDE"
    assert definition["non_key_attributes"] == ["name", "age"]


def test_gsi_to_create_table_definition_missing_attr_raises() -> None:
    """Test GSI to_create_table_definition raises if attribute not on model."""

    # GIVEN a model with GSI referencing non-existent attribute
    class BadModel(Model):
        model_config = ModelConfig(table="test")
        pk = StringAttribute(partition_key=True)

        bad_index = GlobalSecondaryIndex(
            index_name="bad-index",
            partition_key="nonexistent",
        )

    # WHEN we try to get the definition
    # THEN ValueError should be raised
    with pytest.raises(ValueError, match="references attribute 'nonexistent'"):
        BadModel.bad_index.to_create_table_definition(BadModel)
