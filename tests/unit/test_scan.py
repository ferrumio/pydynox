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
    # WHEN calling scan on a model
    result = user_model.scan()

    # THEN it returns a ModelScanResult instance
    assert isinstance(result, ModelScanResult)


def test_scan_stores_parameters(user_model):
    """ModelScanResult stores all scan parameters."""
    # WHEN calling scan with limit and consistent_read
    result = user_model.scan(
        limit=10,
        consistent_read=True,
    )

    # THEN the parameters are stored in the result
    assert result._limit == 10
    assert result._consistent_read is True


def test_scan_with_filter_condition(user_model):
    """Model.scan accepts filter_condition."""
    # GIVEN a filter condition
    condition = user_model.age > 18

    # WHEN calling scan with the filter
    result = user_model.scan(filter_condition=condition)

    # THEN the condition is stored
    assert result._filter_condition is condition


def test_scan_with_pagination(user_model):
    """Model.scan accepts last_evaluated_key for pagination."""
    # GIVEN a last evaluated key from a previous scan
    last_key = {"pk": "USER#123", "sk": "ORDER#999"}

    # WHEN calling scan with the key
    result = user_model.scan(last_evaluated_key=last_key)

    # THEN the key is stored as start_key
    assert result._start_key == last_key


def test_scan_with_parallel_scan_params(user_model):
    """Model.scan accepts segment and total_segments for parallel scan."""
    # WHEN calling scan with parallel scan parameters
    result = user_model.scan(segment=0, total_segments=4)

    # THEN the segment parameters are stored
    assert result._segment == 0
    assert result._total_segments == 4


def test_model_scan_result_first_returns_none_when_empty(user_model):
    """ModelScanResult.first() returns None when no results."""
    # GIVEN a scan that returns no items
    with patch.object(ModelScanResult, "_build_result") as mock_build:
        mock_scan_result = MagicMock()
        mock_scan_result.__iter__ = MagicMock(return_value=iter([]))
        mock_build.return_value = mock_scan_result

        # WHEN calling first()
        result = user_model.scan()
        first = result.first()

        # THEN it returns None
        assert first is None


def test_model_scan_result_list(user_model):
    """list(ModelScanResult) collects all results."""
    # GIVEN a scan that returns multiple items
    with patch.object(ModelScanResult, "_build_result") as mock_build:
        mock_scan_result = MagicMock()
        items = [
            {"pk": "USER#1", "sk": "PROFILE", "name": "Alice", "age": 25},
            {"pk": "USER#2", "sk": "PROFILE", "name": "Bob", "age": 30},
        ]
        mock_scan_result.__iter__ = MagicMock(return_value=iter(items))
        mock_build.return_value = mock_scan_result

        # WHEN converting to list
        result = user_model.scan()
        users = list(result)

        # THEN all items are returned as model instances
        assert len(users) == 2
        assert users[0].name == "Alice"
        assert users[1].name == "Bob"


def test_model_scan_result_iteration(user_model):
    """ModelScanResult can be iterated."""
    # GIVEN a scan that returns one item
    with patch.object(ModelScanResult, "_build_result") as mock_build:
        mock_scan_result = MagicMock()
        items = [
            {"pk": "USER#1", "sk": "PROFILE", "name": "Alice", "age": 25},
        ]
        mock_scan_result.__iter__ = MagicMock(return_value=iter(items))
        mock_build.return_value = mock_scan_result

        # WHEN iterating over the result
        result = user_model.scan()
        users = list(result)

        # THEN items are returned as model instances
        assert len(users) == 1
        assert isinstance(users[0], user_model)


def test_model_scan_result_last_evaluated_key_before_iteration(user_model):
    """ModelScanResult.last_evaluated_key is None before iteration."""
    # WHEN creating a scan result without iterating
    result = user_model.scan()

    # THEN last_evaluated_key is None
    assert result.last_evaluated_key is None


def test_async_scan_returns_async_model_scan_result(user_model):
    """Model.async_scan returns an AsyncModelScanResult."""
    # WHEN calling async_scan on a model
    result = user_model.async_scan()

    # THEN it returns an AsyncModelScanResult instance
    assert isinstance(result, AsyncModelScanResult)


def test_async_scan_stores_parameters(user_model):
    """AsyncModelScanResult stores all scan parameters."""
    # WHEN calling async_scan with various parameters
    result = user_model.async_scan(
        limit=10,
        consistent_read=True,
        segment=1,
        total_segments=4,
    )

    # THEN all parameters are stored
    assert result._limit == 10
    assert result._consistent_read is True
    assert result._segment == 1
    assert result._total_segments == 4


def test_count_calls_client(user_model, mock_client):
    """Model.count calls client.count with correct parameters."""
    # GIVEN a mock client that returns a count
    mock_metrics = MagicMock()
    mock_metrics.duration_ms = 10.0
    mock_metrics.consumed_rcu = 5.0
    mock_client.count.return_value = (42, mock_metrics)

    # WHEN calling count on the model
    count, _ = user_model.count()

    # THEN the client is called and count is returned
    assert count == 42
    mock_client.count.assert_called_once()


def test_count_with_filter(user_model, mock_client):
    """Model.count accepts filter_condition."""
    # GIVEN a mock client and a filter condition
    mock_metrics = MagicMock()
    mock_metrics.duration_ms = 10.0
    mock_metrics.consumed_rcu = 5.0
    mock_client.count.return_value = (10, mock_metrics)
    condition = user_model.age >= 18

    # WHEN calling count with the filter
    count, _ = user_model.count(filter_condition=condition)

    # THEN the filter is passed to the client
    assert count == 10
    call_kwargs = mock_client.count.call_args[1]
    assert call_kwargs["filter_expression"] is not None


def test_count_with_consistent_read(user_model, mock_client):
    """Model.count accepts consistent_read parameter."""
    # GIVEN a mock client
    mock_metrics = MagicMock()
    mock_client.count.return_value = (5, mock_metrics)

    # WHEN calling count with consistent_read=True
    user_model.count(consistent_read=True)

    # THEN consistent_read is passed to the client
    call_kwargs = mock_client.count.call_args[1]
    assert call_kwargs["consistent_read"] is True


# ========== as_dict tests ==========


def test_scan_as_dict_default_is_false(user_model):
    """scan() defaults as_dict to False."""
    # WHEN calling scan without as_dict parameter
    result = user_model.scan()

    # THEN as_dict defaults to False
    assert result._as_dict is False


def test_scan_as_dict_stores_parameter(user_model):
    """ModelScanResult stores as_dict parameter."""
    # WHEN calling scan with as_dict=True
    result = user_model.scan(as_dict=True)

    # THEN the parameter is stored
    assert result._as_dict is True


def test_scan_as_dict_true_returns_dicts(user_model):
    """scan(as_dict=True) returns plain dicts."""
    # GIVEN a scan that returns items
    with patch.object(ModelScanResult, "_build_result") as mock_build:
        mock_scan_result = MagicMock()
        items = [{"pk": "USER#1", "sk": "PROFILE", "name": "Alice", "age": 30}]
        mock_scan_result.__iter__ = MagicMock(return_value=iter(items))
        mock_build.return_value = mock_scan_result

        # WHEN calling scan with as_dict=True
        result = user_model.scan(as_dict=True)
        users = list(result)

        # THEN items are returned as plain dicts
        assert len(users) == 1
        assert isinstance(users[0], dict)
        assert users[0]["name"] == "Alice"


def test_scan_as_dict_false_returns_model_instances(user_model):
    """scan(as_dict=False) returns Model instances."""
    # GIVEN a scan that returns items
    with patch.object(ModelScanResult, "_build_result") as mock_build:
        mock_scan_result = MagicMock()
        items = [{"pk": "USER#1", "sk": "PROFILE", "name": "Alice", "age": 30}]
        mock_scan_result.__iter__ = MagicMock(return_value=iter(items))
        mock_build.return_value = mock_scan_result

        # WHEN calling scan with as_dict=False
        result = user_model.scan(as_dict=False)
        users = list(result)

        # THEN items are returned as model instances
        assert len(users) == 1
        assert isinstance(users[0], user_model)


def test_async_scan_as_dict_stores_parameter(user_model):
    """AsyncModelScanResult stores as_dict parameter."""
    # WHEN calling async_scan with as_dict=True
    result = user_model.async_scan(as_dict=True)

    # THEN the parameter is stored
    assert result._as_dict is True


def test_parallel_scan_as_dict_true_returns_dicts(user_model, mock_client):
    """parallel_scan(as_dict=True) returns plain dicts."""
    # GIVEN a mock client that returns items
    mock_metrics = MagicMock()
    mock_client.parallel_scan.return_value = (
        [
            {"pk": "USER#1", "sk": "PROFILE", "name": "Alice", "age": 30},
            {"pk": "USER#2", "sk": "PROFILE", "name": "Bob", "age": 25},
        ],
        mock_metrics,
    )

    # WHEN calling parallel_scan with as_dict=True
    users, _ = user_model.parallel_scan(total_segments=2, as_dict=True)

    # THEN items are returned as plain dicts
    assert len(users) == 2
    assert isinstance(users[0], dict)
    assert isinstance(users[1], dict)


def test_parallel_scan_as_dict_false_returns_model_instances(user_model, mock_client):
    """parallel_scan(as_dict=False) returns Model instances."""
    # GIVEN a mock client that returns items
    mock_metrics = MagicMock()
    mock_client.parallel_scan.return_value = (
        [
            {"pk": "USER#1", "sk": "PROFILE", "name": "Alice", "age": 30},
        ],
        mock_metrics,
    )

    # WHEN calling parallel_scan with as_dict=False
    users, _ = user_model.parallel_scan(total_segments=2, as_dict=False)

    # THEN items are returned as model instances
    assert len(users) == 1
    assert isinstance(users[0], user_model)
