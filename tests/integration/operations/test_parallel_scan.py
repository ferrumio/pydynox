"""Integration tests for parallel scan operations."""

import pytest
from pydynox import Model, ModelConfig, set_default_client
from pydynox.attributes import NumberAttribute, StringAttribute

PARALLEL_SCAN_TABLE = "parallel_scan_test_table"


@pytest.fixture
def parallel_scan_table(dynamo):
    """Create a dedicated table for parallel scan tests."""
    if not dynamo.table_exists(PARALLEL_SCAN_TABLE):
        dynamo.create_table(
            PARALLEL_SCAN_TABLE,
            hash_key=("pk", "S"),
            range_key=("sk", "S"),
            wait=True,
        )
    yield dynamo
    # Cleanup: delete all items after test
    items = list(dynamo.scan(PARALLEL_SCAN_TABLE))
    for item in items:
        dynamo.delete_item(PARALLEL_SCAN_TABLE, {"pk": item["pk"], "sk": item["sk"]})


@pytest.fixture
def user_model(parallel_scan_table):
    """Create a User model for testing."""
    set_default_client(parallel_scan_table)

    class User(Model):
        model_config = ModelConfig(table=PARALLEL_SCAN_TABLE)
        pk = StringAttribute(hash_key=True)
        sk = StringAttribute(range_key=True)
        name = StringAttribute()
        age = NumberAttribute()
        status = StringAttribute()

    User._client_instance = None
    return User


@pytest.fixture
def populated_users(parallel_scan_table, user_model):
    """Create test data for parallel scan tests."""
    items = [
        {"pk": "USER#1", "sk": "PROFILE", "name": "Alice", "age": 25, "status": "active"},
        {"pk": "USER#2", "sk": "PROFILE", "name": "Bob", "age": 30, "status": "active"},
        {"pk": "USER#3", "sk": "PROFILE", "name": "Charlie", "age": 17, "status": "inactive"},
        {"pk": "USER#4", "sk": "PROFILE", "name": "Diana", "age": 22, "status": "active"},
        {"pk": "USER#5", "sk": "PROFILE", "name": "Eve", "age": 35, "status": "inactive"},
    ]
    for item in items:
        parallel_scan_table.put_item(PARALLEL_SCAN_TABLE, item)
    return user_model


def test_parallel_scan_all_items(populated_users):
    """Test parallel_scan returns all items."""
    User = populated_users

    users, metrics = User.parallel_scan(total_segments=2)

    assert len(users) == 5
    for user in users:
        assert isinstance(user, User)
    assert metrics.duration_ms > 0


def test_parallel_scan_with_filter(populated_users):
    """Test parallel_scan with filter_condition."""
    User = populated_users

    users, metrics = User.parallel_scan(total_segments=2, filter_condition=User.status == "active")

    assert len(users) == 3
    for user in users:
        assert user.status == "active"
    assert metrics.duration_ms > 0


def test_parallel_scan_with_numeric_filter(populated_users):
    """Test parallel_scan with numeric filter."""
    User = populated_users

    users, metrics = User.parallel_scan(total_segments=2, filter_condition=User.age >= 25)

    assert len(users) == 3
    for user in users:
        assert user.age >= 25
    assert metrics.duration_ms > 0


def test_parallel_scan_with_complex_filter(populated_users):
    """Test parallel_scan with complex filter condition."""
    User = populated_users

    users, metrics = User.parallel_scan(
        total_segments=2, filter_condition=(User.status == "active") & (User.age >= 25)
    )

    assert len(users) == 2
    for user in users:
        assert user.status == "active"
        assert user.age >= 25
    assert metrics.duration_ms > 0


def test_parallel_scan_single_segment(populated_users):
    """Test parallel_scan with single segment (should work like regular scan)."""
    User = populated_users

    users, metrics = User.parallel_scan(total_segments=1)

    assert len(users) == 5
    assert metrics.duration_ms > 0


def test_parallel_scan_many_segments(populated_users):
    """Test parallel_scan with many segments."""
    User = populated_users

    users, metrics = User.parallel_scan(total_segments=8)

    assert len(users) == 5
    assert metrics.duration_ms > 0


@pytest.mark.asyncio
async def test_async_parallel_scan_all_items(populated_users):
    """Test async_parallel_scan returns all items."""
    User = populated_users

    users, metrics = await User.async_parallel_scan(total_segments=2)

    assert len(users) == 5
    for user in users:
        assert isinstance(user, User)
    assert metrics.duration_ms > 0


@pytest.mark.asyncio
async def test_async_parallel_scan_with_filter(populated_users):
    """Test async_parallel_scan with filter_condition."""
    User = populated_users

    users, metrics = await User.async_parallel_scan(
        total_segments=2, filter_condition=User.status == "active"
    )

    assert len(users) == 3
    for user in users:
        assert user.status == "active"
    assert metrics.duration_ms > 0


@pytest.mark.asyncio
async def test_async_parallel_scan_with_numeric_filter(populated_users):
    """Test async_parallel_scan with numeric filter."""
    User = populated_users

    users, metrics = await User.async_parallel_scan(
        total_segments=2, filter_condition=User.age >= 25
    )

    assert len(users) == 3
    for user in users:
        assert user.age >= 25
    assert metrics.duration_ms > 0


# ========== as_dict tests ==========


def test_parallel_scan_as_dict_returns_dicts(populated_users):
    """Test parallel_scan(as_dict=True) returns plain dicts."""
    User = populated_users

    users, metrics = User.parallel_scan(total_segments=2, as_dict=True)

    assert len(users) == 5
    for user in users:
        assert isinstance(user, dict)
        assert "pk" in user
        assert "name" in user
    assert metrics.duration_ms > 0


def test_parallel_scan_as_dict_false_returns_models(populated_users):
    """Test parallel_scan(as_dict=False) returns Model instances."""
    User = populated_users

    users, metrics = User.parallel_scan(total_segments=2, as_dict=False)

    assert len(users) == 5
    for user in users:
        assert isinstance(user, User)


def test_parallel_scan_as_dict_with_filter(populated_users):
    """Test parallel_scan(as_dict=True) works with filter_condition."""
    User = populated_users

    users, metrics = User.parallel_scan(
        total_segments=2,
        filter_condition=User.status == "active",
        as_dict=True,
    )

    assert len(users) == 3
    for user in users:
        assert isinstance(user, dict)
        assert user["status"] == "active"


@pytest.mark.asyncio
async def test_async_parallel_scan_as_dict_returns_dicts(populated_users):
    """Test async_parallel_scan(as_dict=True) returns plain dicts."""
    User = populated_users

    users, metrics = await User.async_parallel_scan(total_segments=2, as_dict=True)

    assert len(users) == 5
    for user in users:
        assert isinstance(user, dict)
