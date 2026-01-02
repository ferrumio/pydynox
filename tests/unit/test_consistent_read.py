"""Tests for consistent_read toggle feature."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from pydynox import Model, ModelConfig
from pydynox.attributes import StringAttribute


@pytest.fixture
def mock_client():
    """Create a mock DynamoDB client."""
    client = MagicMock()
    client.get_item.return_value = None
    return client


def test_model_config_consistent_read_default():
    """ModelConfig.consistent_read defaults to False."""
    config = ModelConfig(table="test")
    assert config.consistent_read is False


def test_model_config_consistent_read_true():
    """ModelConfig.consistent_read can be set to True."""
    config = ModelConfig(table="test", consistent_read=True)
    assert config.consistent_read is True


def test_model_get_uses_config_consistent_read(mock_client):
    """Model.get() uses model_config.consistent_read when not specified."""

    class User(Model):
        model_config = ModelConfig(table="users", client=mock_client, consistent_read=True)
        pk = StringAttribute(hash_key=True)
        name = StringAttribute()

    User.get(pk="USER#123")

    mock_client.get_item.assert_called_once()
    call_kwargs = mock_client.get_item.call_args
    assert call_kwargs[1]["consistent_read"] is True


def test_model_get_override_consistent_read(mock_client):
    """Model.get() can override model_config.consistent_read."""

    class User(Model):
        model_config = ModelConfig(table="users", client=mock_client, consistent_read=True)
        pk = StringAttribute(hash_key=True)
        name = StringAttribute()

    # Override to False
    User.get(pk="USER#123", consistent_read=False)

    mock_client.get_item.assert_called_once()
    call_kwargs = mock_client.get_item.call_args
    assert call_kwargs[1]["consistent_read"] is False


def test_model_get_default_eventually_consistent(mock_client):
    """Model.get() defaults to eventually consistent when not configured."""

    class User(Model):
        model_config = ModelConfig(table="users", client=mock_client)
        pk = StringAttribute(hash_key=True)
        name = StringAttribute()

    User.get(pk="USER#123")

    mock_client.get_item.assert_called_once()
    call_kwargs = mock_client.get_item.call_args
    assert call_kwargs[1]["consistent_read"] is False


def test_model_get_explicit_consistent_read(mock_client):
    """Model.get() can request consistent read explicitly."""

    class User(Model):
        model_config = ModelConfig(table="users", client=mock_client)
        pk = StringAttribute(hash_key=True)
        name = StringAttribute()

    User.get(pk="USER#123", consistent_read=True)

    mock_client.get_item.assert_called_once()
    call_kwargs = mock_client.get_item.call_args
    assert call_kwargs[1]["consistent_read"] is True
