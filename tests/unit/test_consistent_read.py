"""Tests for consistent_read toggle feature."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from pydynox import Model, ModelConfig
from pydynox.attributes import StringAttribute


def test_model_config_consistent_read_default():
    """ModelConfig.consistent_read defaults to False."""
    # WHEN we create a ModelConfig without consistent_read
    config = ModelConfig(table="test")

    # THEN consistent_read should default to False
    assert config.consistent_read is False


def test_model_config_consistent_read_true():
    """ModelConfig.consistent_read can be set to True."""
    # WHEN we create a ModelConfig with consistent_read=True
    config = ModelConfig(table="test", consistent_read=True)

    # THEN consistent_read should be True
    assert config.consistent_read is True


@pytest.mark.asyncio
async def test_model_get_uses_config_consistent_read():
    """Model.get() uses model_config.consistent_read when not specified."""
    # GIVEN a model with consistent_read=True in config
    mock_client = MagicMock()
    get_calls = []

    async def mock_get_item(table, key, consistent_read=False):
        get_calls.append({"table": table, "key": key, "consistent_read": consistent_read})
        return None

    mock_client.get_item = mock_get_item

    class User(Model):
        model_config = ModelConfig(table="users", client=mock_client, consistent_read=True)
        pk = StringAttribute(partition_key=True)
        name = StringAttribute()

    User._client_instance = None

    # WHEN we call get without specifying consistent_read
    await User.get(pk="USER#123")

    # THEN the client should be called with consistent_read=True
    assert len(get_calls) == 1
    assert get_calls[0]["consistent_read"] is True


@pytest.mark.asyncio
async def test_model_get_override_consistent_read():
    """Model.get() can override model_config.consistent_read."""
    # GIVEN a model with consistent_read=True in config
    mock_client = MagicMock()
    get_calls = []

    async def mock_get_item(table, key, consistent_read=False):
        get_calls.append({"table": table, "key": key, "consistent_read": consistent_read})
        return None

    mock_client.get_item = mock_get_item

    class User(Model):
        model_config = ModelConfig(table="users", client=mock_client, consistent_read=True)
        pk = StringAttribute(partition_key=True)
        name = StringAttribute()

    User._client_instance = None

    # WHEN we call get with consistent_read=False
    await User.get(pk="USER#123", consistent_read=False)

    # THEN the client should be called with consistent_read=False
    assert len(get_calls) == 1
    assert get_calls[0]["consistent_read"] is False


@pytest.mark.asyncio
async def test_model_get_default_eventually_consistent():
    """Model.get() defaults to eventually consistent when not configured."""
    # GIVEN a model without consistent_read in config
    mock_client = MagicMock()
    get_calls = []

    async def mock_get_item(table, key, consistent_read=False):
        get_calls.append({"table": table, "key": key, "consistent_read": consistent_read})
        return None

    mock_client.get_item = mock_get_item

    class User(Model):
        model_config = ModelConfig(table="users", client=mock_client)
        pk = StringAttribute(partition_key=True)
        name = StringAttribute()

    User._client_instance = None

    # WHEN we call get
    await User.get(pk="USER#123")

    # THEN the client should be called with consistent_read=False
    assert len(get_calls) == 1
    assert get_calls[0]["consistent_read"] is False


@pytest.mark.asyncio
async def test_model_get_explicit_consistent_read():
    """Model.get() can request consistent read explicitly."""
    # GIVEN a model without consistent_read in config
    mock_client = MagicMock()
    get_calls = []

    async def mock_get_item(table, key, consistent_read=False):
        get_calls.append({"table": table, "key": key, "consistent_read": consistent_read})
        return None

    mock_client.get_item = mock_get_item

    class User(Model):
        model_config = ModelConfig(table="users", client=mock_client)
        pk = StringAttribute(partition_key=True)
        name = StringAttribute()

    User._client_instance = None

    # WHEN we call get with consistent_read=True
    await User.get(pk="USER#123", consistent_read=True)

    # THEN the client should be called with consistent_read=True
    assert len(get_calls) == 1
    assert get_calls[0]["consistent_read"] is True
