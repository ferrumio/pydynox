"""Tests for Model.query() method."""

from unittest.mock import MagicMock, patch

import pytest
from pydynox import Model, ModelConfig, clear_default_client
from pydynox.attributes import NumberAttribute, StringAttribute
from pydynox.model import AsyncModelQueryResult, ModelQueryResult


@pytest.fixture(autouse=True)
def reset_state():
    """Reset default client before and after each test."""
    clear_default_client()
    yield
    clear_default_client()


@pytest.fixture
def mock_client():
    """Create a mock DynamoDB client."""
    client = MagicMock()
    client._client = MagicMock()
    client._acquire_rcu = MagicMock()
    return client


@pytest.fixture
def user_model(mock_client):
    """Create a User model with mock client."""

    class User(Model):
        model_config = ModelConfig(table="users", client=mock_client)
        pk = StringAttribute(hash_key=True)
        sk = StringAttribute(range_key=True)
        name = StringAttribute()
        age = NumberAttribute()

    User._client_instance = None
    return User


def test_query_returns_model_query_result(user_model):
    """Model.query returns a ModelQueryResult."""
    result = user_model.query(hash_key="USER#123")

    assert isinstance(result, ModelQueryResult)


def test_query_stores_parameters(user_model):
    """ModelQueryResult stores all query parameters."""
    result = user_model.query(
        hash_key="USER#123",
        limit=10,
        scan_index_forward=False,
        consistent_read=True,
    )

    assert result._hash_key_value == "USER#123"
    assert result._limit == 10
    assert result._scan_index_forward is False
    assert result._consistent_read is True


def test_query_with_range_key_condition(user_model):
    """Model.query accepts range_key_condition."""
    condition = user_model.sk.begins_with("ORDER#")

    result = user_model.query(
        hash_key="USER#123",
        range_key_condition=condition,
    )

    assert result._range_key_condition is condition


def test_query_with_filter_condition(user_model):
    """Model.query accepts filter_condition."""
    condition = user_model.age > 18

    result = user_model.query(
        hash_key="USER#123",
        filter_condition=condition,
    )

    assert result._filter_condition is condition


def test_query_with_pagination(user_model):
    """Model.query accepts last_evaluated_key for pagination."""
    last_key = {"pk": "USER#123", "sk": "ORDER#999"}

    result = user_model.query(
        hash_key="USER#123",
        last_evaluated_key=last_key,
    )

    assert result._start_key == last_key


def test_model_query_result_first_returns_none_when_empty(user_model):
    """ModelQueryResult.first() returns None when no results."""
    with patch.object(ModelQueryResult, "_build_result") as mock_build:
        mock_query_result = MagicMock()
        mock_query_result.__iter__ = MagicMock(return_value=iter([]))
        mock_build.return_value = mock_query_result

        result = user_model.query(hash_key="USER#123")
        first = result.first()

        assert first is None


def test_model_query_result_list(user_model):
    """list(ModelQueryResult) collects all results."""
    with patch.object(ModelQueryResult, "_build_result") as mock_build:
        mock_query_result = MagicMock()
        items = [
            {"pk": "USER#123", "sk": "ORDER#1", "name": "Order 1"},
            {"pk": "USER#123", "sk": "ORDER#2", "name": "Order 2"},
        ]
        mock_query_result.__iter__ = MagicMock(return_value=iter(items))
        mock_build.return_value = mock_query_result

        result = user_model.query(hash_key="USER#123")
        users = list(result)

        assert len(users) == 2
        assert users[0].sk == "ORDER#1"
        assert users[1].sk == "ORDER#2"


def test_model_query_result_iteration(user_model):
    """ModelQueryResult can be iterated."""
    with patch.object(ModelQueryResult, "_build_result") as mock_build:
        mock_query_result = MagicMock()
        items = [
            {"pk": "USER#123", "sk": "ORDER#1", "name": "Order 1"},
        ]
        mock_query_result.__iter__ = MagicMock(return_value=iter(items))
        mock_build.return_value = mock_query_result

        result = user_model.query(hash_key="USER#123")
        users = list(result)

        assert len(users) == 1
        assert isinstance(users[0], user_model)


def test_model_query_result_last_evaluated_key_before_iteration(user_model):
    """ModelQueryResult.last_evaluated_key is None before iteration."""
    result = user_model.query(hash_key="USER#123")

    assert result.last_evaluated_key is None


def test_async_query_returns_async_model_query_result(user_model):
    """Model.async_query returns an AsyncModelQueryResult."""
    result = user_model.async_query(hash_key="USER#123")

    assert isinstance(result, AsyncModelQueryResult)


def test_async_query_stores_parameters(user_model):
    """AsyncModelQueryResult stores all query parameters."""
    result = user_model.async_query(
        hash_key="USER#123",
        limit=10,
        scan_index_forward=False,
        consistent_read=True,
    )

    assert result._hash_key_value == "USER#123"
    assert result._limit == 10
    assert result._scan_index_forward is False
    assert result._consistent_read is True


def test_query_raises_error_without_hash_key(mock_client):
    """Model.query raises error if model has no hash key."""

    class BadModel(Model):
        model_config = ModelConfig(table="bad", client=mock_client)
        name = StringAttribute()

    BadModel._client_instance = None

    result = BadModel.query(hash_key="test")

    with pytest.raises(ValueError, match="has no hash key defined"):
        result.first()


# ========== as_dict tests ==========


def test_query_as_dict_default_is_false(user_model):
    """query() defaults as_dict to False."""
    result = user_model.query(hash_key="USER#123")
    assert result._as_dict is False


def test_query_as_dict_stores_parameter(user_model):
    """ModelQueryResult stores as_dict parameter."""
    result = user_model.query(hash_key="USER#123", as_dict=True)
    assert result._as_dict is True


def test_query_as_dict_true_returns_dicts(user_model):
    """query(as_dict=True) returns plain dicts."""
    with patch.object(ModelQueryResult, "_build_result") as mock_build:
        mock_query_result = MagicMock()
        items = [{"pk": "USER#123", "sk": "ORDER#1", "name": "Order 1", "age": 10}]
        mock_query_result.__iter__ = MagicMock(return_value=iter(items))
        mock_build.return_value = mock_query_result

        result = user_model.query(hash_key="USER#123", as_dict=True)
        orders = list(result)

        assert len(orders) == 1
        assert isinstance(orders[0], dict)
        assert orders[0]["name"] == "Order 1"


def test_query_as_dict_false_returns_model_instances(user_model):
    """query(as_dict=False) returns Model instances."""
    with patch.object(ModelQueryResult, "_build_result") as mock_build:
        mock_query_result = MagicMock()
        items = [{"pk": "USER#123", "sk": "ORDER#1", "name": "Order 1", "age": 10}]
        mock_query_result.__iter__ = MagicMock(return_value=iter(items))
        mock_build.return_value = mock_query_result

        result = user_model.query(hash_key="USER#123", as_dict=False)
        orders = list(result)

        assert len(orders) == 1
        assert isinstance(orders[0], user_model)


def test_async_query_as_dict_stores_parameter(user_model):
    """AsyncModelQueryResult stores as_dict parameter."""
    result = user_model.async_query(hash_key="USER#123", as_dict=True)
    assert result._as_dict is True
