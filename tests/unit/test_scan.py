"""Tests for Model.scan() and Model.count() methods."""

from unittest.mock import MagicMock, patch

import pytest
from pydynox import Model, ModelConfig, clear_default_client
from pydynox.attributes import NumberAttribute, StringAttribute
from pydynox.model import AsyncModelScanResult, ModelScanResult


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


def test_scan_returns_model_scan_result(user_model):
    """Model.scan returns a ModelScanResult."""
    result = user_model.scan()

    assert isinstance(result, ModelScanResult)


def test_scan_stores_parameters(user_model):
    """ModelScanResult stores all scan parameters."""
    result = user_model.scan(
        limit=10,
        consistent_read=True,
    )

    assert result._limit == 10
    assert result._consistent_read is True


def test_scan_with_filter_condition(user_model):
    """Model.scan accepts filter_condition."""
    condition = user_model.age > 18

    result = user_model.scan(filter_condition=condition)

    assert result._filter_condition is condition


def test_scan_with_pagination(user_model):
    """Model.scan accepts last_evaluated_key for pagination."""
    last_key = {"pk": "USER#123", "sk": "ORDER#999"}

    result = user_model.scan(last_evaluated_key=last_key)

    assert result._start_key == last_key


def test_scan_with_parallel_scan_params(user_model):
    """Model.scan accepts segment and total_segments for parallel scan."""
    result = user_model.scan(segment=0, total_segments=4)

    assert result._segment == 0
    assert result._total_segments == 4


def test_model_scan_result_first_returns_none_when_empty(user_model):
    """ModelScanResult.first() returns None when no results."""
    with patch.object(ModelScanResult, "_build_result") as mock_build:
        mock_scan_result = MagicMock()
        mock_scan_result.__iter__ = MagicMock(return_value=iter([]))
        mock_build.return_value = mock_scan_result

        result = user_model.scan()
        first = result.first()

        assert first is None


def test_model_scan_result_list(user_model):
    """list(ModelScanResult) collects all results."""
    with patch.object(ModelScanResult, "_build_result") as mock_build:
        mock_scan_result = MagicMock()
        items = [
            {"pk": "USER#1", "sk": "PROFILE", "name": "Alice", "age": 25},
            {"pk": "USER#2", "sk": "PROFILE", "name": "Bob", "age": 30},
        ]
        mock_scan_result.__iter__ = MagicMock(return_value=iter(items))
        mock_build.return_value = mock_scan_result

        result = user_model.scan()
        users = list(result)

        assert len(users) == 2
        assert users[0].name == "Alice"
        assert users[1].name == "Bob"


def test_model_scan_result_iteration(user_model):
    """ModelScanResult can be iterated."""
    with patch.object(ModelScanResult, "_build_result") as mock_build:
        mock_scan_result = MagicMock()
        items = [
            {"pk": "USER#1", "sk": "PROFILE", "name": "Alice", "age": 25},
        ]
        mock_scan_result.__iter__ = MagicMock(return_value=iter(items))
        mock_build.return_value = mock_scan_result

        result = user_model.scan()
        users = list(result)

        assert len(users) == 1
        assert isinstance(users[0], user_model)


def test_model_scan_result_metrics_before_iteration(user_model):
    """ModelScanResult.metrics is None before iteration."""
    result = user_model.scan()

    assert result.metrics is None


def test_model_scan_result_last_evaluated_key_before_iteration(user_model):
    """ModelScanResult.last_evaluated_key is None before iteration."""
    result = user_model.scan()

    assert result.last_evaluated_key is None


def test_async_scan_returns_async_model_scan_result(user_model):
    """Model.async_scan returns an AsyncModelScanResult."""
    result = user_model.async_scan()

    assert isinstance(result, AsyncModelScanResult)


def test_async_scan_stores_parameters(user_model):
    """AsyncModelScanResult stores all scan parameters."""
    result = user_model.async_scan(
        limit=10,
        consistent_read=True,
        segment=1,
        total_segments=4,
    )

    assert result._limit == 10
    assert result._consistent_read is True
    assert result._segment == 1
    assert result._total_segments == 4


def test_count_calls_client(user_model, mock_client):
    """Model.count calls client.count with correct parameters."""
    mock_metrics = MagicMock()
    mock_metrics.duration_ms = 10.0
    mock_metrics.consumed_rcu = 5.0
    mock_client.count.return_value = (42, mock_metrics)

    count, metrics = user_model.count()

    assert count == 42
    mock_client.count.assert_called_once()


def test_count_with_filter(user_model, mock_client):
    """Model.count accepts filter_condition."""
    mock_metrics = MagicMock()
    mock_metrics.duration_ms = 10.0
    mock_metrics.consumed_rcu = 5.0
    mock_client.count.return_value = (10, mock_metrics)

    condition = user_model.age >= 18
    count, _ = user_model.count(filter_condition=condition)

    assert count == 10
    call_kwargs = mock_client.count.call_args[1]
    assert call_kwargs["filter_expression"] is not None


def test_count_with_consistent_read(user_model, mock_client):
    """Model.count accepts consistent_read parameter."""
    mock_metrics = MagicMock()
    mock_client.count.return_value = (5, mock_metrics)

    user_model.count(consistent_read=True)

    call_kwargs = mock_client.count.call_args[1]
    assert call_kwargs["consistent_read"] is True
