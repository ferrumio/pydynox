"""Unit tests for Model table operations (create_table, table_exists, delete_table)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from pydynox import DynamoDBClient, Model, ModelConfig
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

    email_index = GlobalSecondaryIndex(
        index_name="email-index",
        hash_key="email",
    )

    status_age_index = GlobalSecondaryIndex(
        index_name="status-age-index",
        hash_key="status",
        range_key="age",
    )

    location_index = GlobalSecondaryIndex(
        index_name="location-index",
        hash_key=["tenant_id", "region"],
    )


class SimpleModel(Model):
    """Model with only hash key."""

    model_config = ModelConfig(table="simple")
    pk = StringAttribute(hash_key=True)
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


def test_create_table_basic(mock_client: MagicMock) -> None:
    """Test create_table with basic model."""
    with patch.object(SimpleModel, "_get_client", return_value=mock_client):
        SimpleModel.create_table()

    mock_client.create_table.assert_called_once_with(
        "simple",
        hash_key=("pk", "S"),
        range_key=None,
        billing_mode="PAY_PER_REQUEST",
        read_capacity=None,
        write_capacity=None,
        table_class=None,
        encryption=None,
        kms_key_id=None,
        global_secondary_indexes=None,
        wait=False,
    )


def test_create_table_with_range_key(mock_client: MagicMock) -> None:
    """Test create_table with hash and range key."""

    class WithRange(Model):
        model_config = ModelConfig(table="with_range")
        pk = StringAttribute(hash_key=True)
        sk = NumberAttribute(range_key=True)

    with patch.object(WithRange, "_get_client", return_value=mock_client):
        WithRange.create_table()

    mock_client.create_table.assert_called_once()
    call_args = mock_client.create_table.call_args
    assert call_args[0][0] == "with_range"
    assert call_args[1]["hash_key"] == ("pk", "S")
    assert call_args[1]["range_key"] == ("sk", "N")


def test_create_table_with_gsis(mock_client: MagicMock) -> None:
    """Test create_table includes GSI definitions."""
    with patch.object(User, "_get_client", return_value=mock_client):
        User.create_table()

    mock_client.create_table.assert_called_once()
    call_args = mock_client.create_table.call_args

    gsis = call_args[1]["global_secondary_indexes"]
    assert gsis is not None
    assert len(gsis) == 3

    # Find each GSI by name
    gsi_by_name = {g["index_name"]: g for g in gsis}

    # Single-attribute GSI
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


def test_create_table_with_options(mock_client: MagicMock) -> None:
    """Test create_table with all options."""
    with patch.object(SimpleModel, "_get_client", return_value=mock_client):
        SimpleModel.create_table(
            billing_mode="PROVISIONED",
            read_capacity=10,
            write_capacity=5,
            table_class="STANDARD_INFREQUENT_ACCESS",
            encryption="CUSTOMER_MANAGED",
            kms_key_id="arn:aws:kms:us-east-1:123456789012:key/abc",
            wait=True,
        )

    mock_client.create_table.assert_called_once_with(
        "simple",
        hash_key=("pk", "S"),
        range_key=None,
        billing_mode="PROVISIONED",
        read_capacity=10,
        write_capacity=5,
        table_class="STANDARD_INFREQUENT_ACCESS",
        encryption="CUSTOMER_MANAGED",
        kms_key_id="arn:aws:kms:us-east-1:123456789012:key/abc",
        global_secondary_indexes=None,
        wait=True,
    )


def test_create_table_no_hash_key_raises() -> None:
    """Test create_table raises error if no hash key defined."""
    mock_client = MagicMock(spec=DynamoDBClient)

    with patch.object(NoKeyModel, "_get_client", return_value=mock_client):
        with pytest.raises(ValueError, match="has no hash_key defined"):
            NoKeyModel.create_table()


def test_table_exists(mock_client: MagicMock) -> None:
    """Test table_exists calls client correctly."""
    mock_client.table_exists.return_value = True

    with patch.object(SimpleModel, "_get_client", return_value=mock_client):
        result = SimpleModel.table_exists()

    assert result is True
    mock_client.table_exists.assert_called_once_with("simple")


def test_table_exists_false(mock_client: MagicMock) -> None:
    """Test table_exists returns False when table doesn't exist."""
    mock_client.table_exists.return_value = False

    with patch.object(SimpleModel, "_get_client", return_value=mock_client):
        result = SimpleModel.table_exists()

    assert result is False


def test_delete_table(mock_client: MagicMock) -> None:
    """Test delete_table calls client correctly."""
    with patch.object(SimpleModel, "_get_client", return_value=mock_client):
        SimpleModel.delete_table()

    mock_client.delete_table.assert_called_once_with("simple")


def test_gsi_to_create_table_definition_single_attr() -> None:
    """Test GSI to_create_table_definition with single attribute keys."""
    definition = User.email_index.to_create_table_definition(User)

    assert definition["index_name"] == "email-index"
    assert definition["hash_key"] == ("email", "S")
    assert "range_key" not in definition
    assert definition["projection"] == "ALL"


def test_gsi_to_create_table_definition_with_range() -> None:
    """Test GSI to_create_table_definition with range key."""
    definition = User.status_age_index.to_create_table_definition(User)

    assert definition["index_name"] == "status-age-index"
    assert definition["hash_key"] == ("status", "S")
    assert definition["range_key"] == ("age", "N")


def test_gsi_to_create_table_definition_multi_attr() -> None:
    """Test GSI to_create_table_definition with multi-attribute keys."""
    definition = User.location_index.to_create_table_definition(User)

    assert definition["index_name"] == "location-index"
    assert definition["hash_keys"] == [("tenant_id", "S"), ("region", "S")]
    assert "hash_key" not in definition


def test_gsi_to_create_table_definition_keys_only_projection() -> None:
    """Test GSI to_create_table_definition with KEYS_ONLY projection."""

    class ModelWithKeysOnly(Model):
        model_config = ModelConfig(table="test")
        pk = StringAttribute(hash_key=True)
        email = StringAttribute()

        email_index = GlobalSecondaryIndex(
            index_name="email-index",
            hash_key="email",
            projection="KEYS_ONLY",
        )

    definition = ModelWithKeysOnly.email_index.to_create_table_definition(ModelWithKeysOnly)
    assert definition["projection"] == "KEYS_ONLY"


def test_gsi_to_create_table_definition_include_projection() -> None:
    """Test GSI to_create_table_definition with INCLUDE projection."""

    class ModelWithInclude(Model):
        model_config = ModelConfig(table="test")
        pk = StringAttribute(hash_key=True)
        email = StringAttribute()
        name = StringAttribute()
        age = NumberAttribute()

        email_index = GlobalSecondaryIndex(
            index_name="email-index",
            hash_key="email",
            projection=["name", "age"],
        )

    definition = ModelWithInclude.email_index.to_create_table_definition(ModelWithInclude)
    assert definition["projection"] == "INCLUDE"
    assert definition["non_key_attributes"] == ["name", "age"]


def test_gsi_to_create_table_definition_missing_attr_raises() -> None:
    """Test GSI to_create_table_definition raises if attribute not on model."""

    class BadModel(Model):
        model_config = ModelConfig(table="test")
        pk = StringAttribute(hash_key=True)

        bad_index = GlobalSecondaryIndex(
            index_name="bad-index",
            hash_key="nonexistent",
        )

    with pytest.raises(ValueError, match="references attribute 'nonexistent'"):
        BadModel.bad_index.to_create_table_definition(BadModel)
