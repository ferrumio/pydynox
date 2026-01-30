"""Tests for Model.scan() and Model.count() methods.

With async-first API:
- scan() returns AsyncModelScanResult (async, default)
- sync_scan() returns ModelScanResult (sync)
- count() is async (default)
- sync_count() is sync
"""

from unittest.mock import AsyncMock, MagicMock

import pytest
from pydynox import Model, ModelConfig, clear_default_client
from pydynox._internal._results import AsyncModelScanResult, ModelScanResult
from pydynox.attributes import NumberAttribute, StringAttribute


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
    # Async methods on _client (Rust client)
    client._client.scan_page = AsyncMock(
        return_value={
            "items": [],
            "last_evaluated_key": None,
            "metrics": MagicMock(duration_ms=1.0, consumed_rcu=1.0, items_count=0),
        }
    )
    # Sync methods on _client (Rust client)
    client._client.sync_scan_page = MagicMock(
        return_value=([], None, MagicMock(duration_ms=1.0, consumed_rcu=1.0, items_count=0))
    )
    # Client-level methods (count, parallel_scan)
    client.count = AsyncMock(return_value=(0, MagicMock(duration_ms=1.0, consumed_rcu=1.0)))
    client.parallel_scan = AsyncMock(return_value=([], MagicMock(duration_ms=1.0)))
    client.sync_count = MagicMock(return_value=(0, MagicMock(duration_ms=1.0, consumed_rcu=1.0)))
    client.sync_parallel_scan = MagicMock(return_value=([], MagicMock(duration_ms=1.0)))
    return client


@pytest.fixture
def user_model(mock_client):
    """Create a User model with mock client."""

    class User(Model):
        model_config = ModelConfig(table="users", client=mock_client)
        pk = StringAttribute(partition_key=True)
        sk = StringAttribute(sort_key=True)
        name = StringAttribute()
        age = NumberAttribute()

    User._client_instance = None
    return User


# ========== ASYNC TESTS (scan - default) ==========


def test_scan_returns_async_model_scan_result(user_model):
    """Model.scan() returns an AsyncModelScanResult (async, default)."""
    result = user_model.scan()
    assert isinstance(result, AsyncModelScanResult)


def test_scan_stores_parameters(user_model):
    """AsyncModelScanResult stores all scan parameters."""
    result = user_model.scan(
        limit=10,
        consistent_read=True,
        segment=1,
        total_segments=4,
    )
    assert result._limit == 10
    assert result._consistent_read is True
    assert result._segment == 1
    assert result._total_segments == 4


def test_scan_with_filter_condition(user_model):
    """Model.scan() accepts filter_condition."""
    condition = user_model.age > 18
    result = user_model.scan(filter_condition=condition)
    assert result._filter_condition is condition


def test_scan_with_pagination(user_model):
    """Model.scan() accepts last_evaluated_key for pagination."""
    last_key = {"pk": "USER#123", "sk": "ORDER#999"}
    result = user_model.scan(last_evaluated_key=last_key)
    assert result._start_key == last_key


@pytest.mark.asyncio
async def test_async_scan_first_returns_none_when_empty(user_model, mock_client):
    """AsyncModelScanResult.first() returns None when no results."""
    mock_client._client.scan_page.return_value = {
        "items": [],
        "last_evaluated_key": None,
        "metrics": MagicMock(duration_ms=1.0, consumed_rcu=1.0, items_count=0),
    }

    result = user_model.scan()
    first = await result.first()

    assert first is None


@pytest.mark.asyncio
async def test_async_scan_to_list(user_model, mock_client):
    """AsyncModelScanResult collects all results via async iteration."""
    mock_client._client.scan_page.return_value = {
        "items": [
            {"pk": "USER#1", "sk": "PROFILE", "name": "Alice", "age": 25},
            {"pk": "USER#2", "sk": "PROFILE", "name": "Bob", "age": 30},
        ],
        "last_evaluated_key": None,
        "metrics": MagicMock(duration_ms=1.0, consumed_rcu=1.0, items_count=2),
    }

    result = user_model.scan()
    users = [user async for user in result]

    assert len(users) == 2
    assert users[0].name == "Alice"
    assert users[1].name == "Bob"


@pytest.mark.asyncio
async def test_async_scan_iteration(user_model, mock_client):
    """AsyncModelScanResult can be iterated with async for."""
    mock_client._client.scan_page.return_value = {
        "items": [{"pk": "USER#1", "sk": "PROFILE", "name": "Alice", "age": 25}],
        "last_evaluated_key": None,
        "metrics": MagicMock(duration_ms=1.0, consumed_rcu=1.0, items_count=1),
    }

    result = user_model.scan()
    users = []
    async for user in result:
        users.append(user)

    assert len(users) == 1
    assert isinstance(users[0], user_model)


def test_scan_last_evaluated_key_before_iteration(user_model):
    """AsyncModelScanResult.last_evaluated_key is None before iteration."""
    result = user_model.scan()
    assert result.last_evaluated_key is None


# ========== ASYNC count tests ==========


@pytest.mark.asyncio
async def test_count_calls_client(user_model, mock_client):
    """Model.count() calls client.count (async)."""
    mock_metrics = MagicMock()
    mock_metrics.duration_ms = 10.0
    mock_metrics.consumed_rcu = 5.0
    mock_client.count.return_value = (42, mock_metrics)

    count, _ = await user_model.count()

    assert count == 42
    mock_client.count.assert_called_once()


@pytest.mark.asyncio
async def test_count_with_filter(user_model, mock_client):
    """Model.count() accepts filter_condition (async)."""
    mock_metrics = MagicMock()
    mock_client.count.return_value = (10, mock_metrics)
    condition = user_model.age >= 18

    count, _ = await user_model.count(filter_condition=condition)

    assert count == 10
    call_kwargs = mock_client.count.call_args[1]
    assert call_kwargs["filter_expression"] is not None


@pytest.mark.asyncio
async def test_count_with_consistent_read(user_model, mock_client):
    """Model.count() accepts consistent_read (async)."""
    mock_metrics = MagicMock()
    mock_client.count.return_value = (5, mock_metrics)

    await user_model.count(consistent_read=True)

    call_kwargs = mock_client.count.call_args[1]
    assert call_kwargs["consistent_read"] is True


# ========== ASYNC as_dict tests ==========


def test_scan_as_dict_default_is_false(user_model):
    """scan() defaults as_dict to False."""
    result = user_model.scan()
    assert result._as_dict is False


def test_scan_as_dict_stores_parameter(user_model):
    """AsyncModelScanResult stores as_dict parameter."""
    result = user_model.scan(as_dict=True)
    assert result._as_dict is True


@pytest.mark.asyncio
async def test_scan_as_dict_true_returns_dicts(user_model, mock_client):
    """scan(as_dict=True) returns plain dicts."""
    mock_client._client.scan_page.return_value = {
        "items": [{"pk": "USER#1", "sk": "PROFILE", "name": "Alice", "age": 30}],
        "last_evaluated_key": None,
        "metrics": MagicMock(duration_ms=1.0, consumed_rcu=1.0, items_count=1),
    }

    result = user_model.scan(as_dict=True)
    users = [user async for user in result]

    assert len(users) == 1
    assert isinstance(users[0], dict)
    assert users[0]["name"] == "Alice"


@pytest.mark.asyncio
async def test_scan_as_dict_false_returns_model_instances(user_model, mock_client):
    """scan(as_dict=False) returns Model instances."""
    mock_client._client.scan_page.return_value = {
        "items": [{"pk": "USER#1", "sk": "PROFILE", "name": "Alice", "age": 30}],
        "last_evaluated_key": None,
        "metrics": MagicMock(duration_ms=1.0, consumed_rcu=1.0, items_count=1),
    }

    result = user_model.scan(as_dict=False)
    users = [user async for user in result]

    assert len(users) == 1
    assert isinstance(users[0], user_model)


# ========== ASYNC parallel_scan tests ==========


@pytest.mark.asyncio
async def test_parallel_scan_as_dict_true_returns_dicts(user_model, mock_client):
    """parallel_scan(as_dict=True) returns plain dicts (async)."""
    mock_metrics = MagicMock()
    mock_client.parallel_scan.return_value = (
        [
            {"pk": "USER#1", "sk": "PROFILE", "name": "Alice", "age": 30},
            {"pk": "USER#2", "sk": "PROFILE", "name": "Bob", "age": 25},
        ],
        mock_metrics,
    )

    users, _ = await user_model.parallel_scan(total_segments=2, as_dict=True)

    assert len(users) == 2
    assert isinstance(users[0], dict)
    assert isinstance(users[1], dict)


@pytest.mark.asyncio
async def test_parallel_scan_as_dict_false_returns_model_instances(user_model, mock_client):
    """parallel_scan(as_dict=False) returns Model instances (async)."""
    mock_metrics = MagicMock()
    mock_client.parallel_scan.return_value = (
        [{"pk": "USER#1", "sk": "PROFILE", "name": "Alice", "age": 30}],
        mock_metrics,
    )

    users, _ = await user_model.parallel_scan(total_segments=2, as_dict=False)

    assert len(users) == 1
    assert isinstance(users[0], user_model)


# ========== SYNC TESTS (sync_scan) ==========


def test_sync_scan_returns_model_scan_result(user_model):
    """Model.sync_scan() returns a ModelScanResult (sync)."""
    result = user_model.sync_scan()
    assert isinstance(result, ModelScanResult)


def test_sync_scan_stores_parameters(user_model):
    """ModelScanResult stores all scan parameters."""
    result = user_model.sync_scan(
        limit=10,
        consistent_read=True,
        segment=1,
        total_segments=4,
    )
    assert result._limit == 10
    assert result._consistent_read is True
    assert result._segment == 1
    assert result._total_segments == 4


def test_sync_scan_first_returns_none_when_empty(user_model, mock_client):
    """ModelScanResult.first() returns None when no results."""
    mock_client._client.sync_scan_page.return_value = (
        [],
        None,
        MagicMock(duration_ms=1.0, consumed_rcu=1.0, items_count=0),
    )

    result = user_model.sync_scan()
    first = result.first()

    assert first is None


def test_sync_scan_list(user_model, mock_client):
    """list(ModelScanResult) collects all results."""
    mock_client._client.sync_scan_page.return_value = (
        [
            {"pk": "USER#1", "sk": "PROFILE", "name": "Alice", "age": 25},
            {"pk": "USER#2", "sk": "PROFILE", "name": "Bob", "age": 30},
        ],
        None,
        MagicMock(duration_ms=1.0, consumed_rcu=1.0, items_count=2),
    )

    result = user_model.sync_scan()
    users = list(result)

    assert len(users) == 2
    assert users[0].name == "Alice"
    assert users[1].name == "Bob"


def test_sync_scan_iteration(user_model, mock_client):
    """ModelScanResult can be iterated."""
    mock_client._client.sync_scan_page.return_value = (
        [{"pk": "USER#1", "sk": "PROFILE", "name": "Alice", "age": 25}],
        None,
        MagicMock(duration_ms=1.0, consumed_rcu=1.0, items_count=1),
    )

    result = user_model.sync_scan()
    users = list(result)

    assert len(users) == 1
    assert isinstance(users[0], user_model)


# ========== SYNC count tests ==========


def test_sync_count_calls_client(user_model, mock_client):
    """Model.sync_count() calls client.sync_count (sync)."""
    mock_metrics = MagicMock()
    mock_client.sync_count.return_value = (42, mock_metrics)

    count, _ = user_model.sync_count()

    assert count == 42
    mock_client.sync_count.assert_called_once()


def test_sync_count_with_filter(user_model, mock_client):
    """Model.sync_count() accepts filter_condition (sync)."""
    mock_metrics = MagicMock()
    mock_client.sync_count.return_value = (10, mock_metrics)
    condition = user_model.age >= 18

    count, _ = user_model.sync_count(filter_condition=condition)

    assert count == 10
    call_kwargs = mock_client.sync_count.call_args[1]
    assert call_kwargs["filter_expression"] is not None


def test_sync_count_with_consistent_read(user_model, mock_client):
    """Model.sync_count() accepts consistent_read (sync)."""
    mock_metrics = MagicMock()
    mock_client.sync_count.return_value = (5, mock_metrics)

    user_model.sync_count(consistent_read=True)

    call_kwargs = mock_client.sync_count.call_args[1]
    assert call_kwargs["consistent_read"] is True


# ========== SYNC as_dict tests ==========


def test_sync_scan_as_dict_true_returns_dicts(user_model, mock_client):
    """sync_scan(as_dict=True) returns plain dicts."""
    mock_client._client.sync_scan_page.return_value = (
        [{"pk": "USER#1", "sk": "PROFILE", "name": "Alice", "age": 30}],
        None,
        MagicMock(duration_ms=1.0, consumed_rcu=1.0, items_count=1),
    )

    result = user_model.sync_scan(as_dict=True)
    users = list(result)

    assert len(users) == 1
    assert isinstance(users[0], dict)
    assert users[0]["name"] == "Alice"


def test_sync_scan_as_dict_false_returns_model_instances(user_model, mock_client):
    """sync_scan(as_dict=False) returns Model instances."""
    mock_client._client.sync_scan_page.return_value = (
        [{"pk": "USER#1", "sk": "PROFILE", "name": "Alice", "age": 30}],
        None,
        MagicMock(duration_ms=1.0, consumed_rcu=1.0, items_count=1),
    )

    result = user_model.sync_scan(as_dict=False)
    users = list(result)

    assert len(users) == 1
    assert isinstance(users[0], user_model)


# ========== SYNC parallel_scan tests ==========


def test_sync_parallel_scan_as_dict_true_returns_dicts(user_model, mock_client):
    """sync_parallel_scan(as_dict=True) returns plain dicts."""
    mock_metrics = MagicMock()
    mock_client.sync_parallel_scan.return_value = (
        [
            {"pk": "USER#1", "sk": "PROFILE", "name": "Alice", "age": 30},
            {"pk": "USER#2", "sk": "PROFILE", "name": "Bob", "age": 25},
        ],
        mock_metrics,
    )

    users, _ = user_model.sync_parallel_scan(total_segments=2, as_dict=True)

    assert len(users) == 2
    assert isinstance(users[0], dict)
    assert isinstance(users[1], dict)


def test_sync_parallel_scan_as_dict_false_returns_model_instances(user_model, mock_client):
    """sync_parallel_scan(as_dict=False) returns Model instances."""
    mock_metrics = MagicMock()
    mock_client.sync_parallel_scan.return_value = (
        [{"pk": "USER#1", "sk": "PROFILE", "name": "Alice", "age": 30}],
        mock_metrics,
    )

    users, _ = user_model.sync_parallel_scan(total_segments=2, as_dict=False)

    assert len(users) == 1
    assert isinstance(users[0], user_model)
