"""Tests for ModelConfig and default client."""

from unittest.mock import MagicMock

import pytest
from pydynox import (
    Model,
    ModelConfig,
    clear_default_client,
    get_default_client,
    set_default_client,
)
from pydynox.attributes import StringAttribute


@pytest.fixture(autouse=True)
def reset_default_client():
    """Reset default client before and after each test."""
    clear_default_client()
    yield
    clear_default_client()


def test_model_config_required_table():
    """ModelConfig requires table name."""
    # WHEN we create a ModelConfig with table name
    config = ModelConfig(table="users")

    # THEN the table should be set
    assert config.table == "users"


def test_model_config_defaults():
    """ModelConfig has sensible defaults."""
    # WHEN we create a ModelConfig with only table
    config = ModelConfig(table="users")

    # THEN defaults should be set correctly
    assert config.client is None
    assert config.skip_hooks is False
    assert config.max_size is None


def test_model_config_with_client():
    """ModelConfig accepts a client."""
    # GIVEN a mock client
    mock_client = MagicMock()

    # WHEN we create a ModelConfig with the client
    config = ModelConfig(table="users", client=mock_client)

    # THEN the client should be set
    assert config.client is mock_client


def test_model_config_with_options():
    """ModelConfig accepts all options."""
    # GIVEN a mock client and various options
    mock_client = MagicMock()

    # WHEN we create a ModelConfig with all options
    config = ModelConfig(
        table="users",
        client=mock_client,
        skip_hooks=True,
        max_size=400000,
    )

    # THEN all options should be set correctly
    assert config.table == "users"
    assert config.client is mock_client
    assert config.skip_hooks is True
    assert config.max_size == 400000


def test_set_default_client():
    """set_default_client sets the global client."""
    # GIVEN a mock client
    mock_client = MagicMock()

    # WHEN we set it as default
    set_default_client(mock_client)

    # THEN it should be retrievable
    assert get_default_client() is mock_client


def test_get_default_client_returns_none_when_not_set():
    """get_default_client returns None when no client is set."""
    # GIVEN no default client is set

    # WHEN we get the default client
    # THEN None should be returned
    assert get_default_client() is None


def test_clear_default_client():
    """clear_default_client removes the global client."""
    # GIVEN a default client is set
    mock_client = MagicMock()
    set_default_client(mock_client)

    # WHEN we clear the default client
    clear_default_client()

    # THEN get_default_client should return None
    assert get_default_client() is None


def test_model_uses_config_client():
    """Model uses client from model_config."""
    # GIVEN a model with a mock client configured
    mock_client = MagicMock()
    mock_client.get_item.return_value = {"pk": "USER#1", "name": "John"}

    class User(Model):
        model_config = ModelConfig(table="users", client=mock_client)
        pk = StringAttribute(hash_key=True)
        name = StringAttribute()

    User._client_instance = None

    # WHEN we call get
    User.get(pk="USER#1")

    # THEN the mock client should be called with correct params
    mock_client.get_item.assert_called_once_with("users", {"pk": "USER#1"}, consistent_read=False)


def test_model_uses_default_client_when_no_config_client():
    """Model uses default client when model_config.client is None."""
    # GIVEN a default client is set
    mock_client = MagicMock()
    mock_client.get_item.return_value = {"pk": "USER#1", "name": "John"}
    set_default_client(mock_client)

    class User(Model):
        model_config = ModelConfig(table="users")
        pk = StringAttribute(hash_key=True)
        name = StringAttribute()

    User._client_instance = None

    # WHEN we call get
    User.get(pk="USER#1")

    # THEN the default client should be used
    mock_client.get_item.assert_called_once_with("users", {"pk": "USER#1"}, consistent_read=False)


def test_model_config_client_takes_priority_over_default():
    """model_config.client takes priority over default client."""
    # GIVEN both a default client and a config client
    default_client = MagicMock()
    config_client = MagicMock()
    config_client.get_item.return_value = {"pk": "USER#1", "name": "John"}

    set_default_client(default_client)

    class User(Model):
        model_config = ModelConfig(table="users", client=config_client)
        pk = StringAttribute(hash_key=True)
        name = StringAttribute()

    User._client_instance = None

    # WHEN we call get
    User.get(pk="USER#1")

    # THEN the config client should be used, not the default
    config_client.get_item.assert_called_once()
    default_client.get_item.assert_not_called()


def test_model_raises_error_when_no_client():
    """Model raises error when no client is configured."""

    # GIVEN a model with no client configured
    class User(Model):
        model_config = ModelConfig(table="users")
        pk = StringAttribute(hash_key=True)
        name = StringAttribute()

    User._client_instance = None

    # WHEN we try to call get
    # THEN ValueError should be raised
    with pytest.raises(ValueError, match="No client configured"):
        User.get(pk="USER#1")


def test_model_raises_error_when_no_model_config():
    """Model raises error when model_config is not defined."""

    # GIVEN a model without model_config
    class User(Model):
        pk = StringAttribute(hash_key=True)
        name = StringAttribute()

    User._client_instance = None
    mock_client = MagicMock()
    set_default_client(mock_client)

    # WHEN we try to call get
    # THEN ValueError should be raised
    with pytest.raises(ValueError, match="must define model_config"):
        User.get(pk="USER#1")


def test_model_skip_hooks_from_config():
    """Model respects skip_hooks from model_config."""
    # GIVEN a model with skip_hooks=True in config
    mock_client = MagicMock()

    class User(Model):
        model_config = ModelConfig(table="users", client=mock_client, skip_hooks=True)
        pk = StringAttribute(hash_key=True)
        name = StringAttribute()

    User._client_instance = None
    user = User(pk="USER#1", name="John")

    # THEN skip_hooks should be True from config
    assert user._should_skip_hooks(None) is True

    # AND can be overridden per-call
    assert user._should_skip_hooks(False) is False


def test_model_get_table_from_config():
    """Model gets table name from model_config."""
    # GIVEN a model with a specific table name
    mock_client = MagicMock()

    class User(Model):
        model_config = ModelConfig(table="my_users_table", client=mock_client)
        pk = StringAttribute(hash_key=True)

    # THEN _get_table should return the configured table name
    assert User._get_table() == "my_users_table"
