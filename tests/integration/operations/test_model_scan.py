"""Integration tests for Model.scan() and Model.count() methods.

Uses a dedicated table (scan_test_table) to avoid conflicts with other tests.
Scan reads ALL items in a table, so it cannot share tables with other tests.
"""

import pytest
from pydynox import Model, ModelConfig, set_default_client
from pydynox.attributes import NumberAttribute, StringAttribute

SCAN_TABLE = "scan_test_table"


@pytest.fixture
def scan_table(dynamo):
    """Create a dedicated table for scan tests."""
    if not dynamo.table_exists(SCAN_TABLE):
        dynamo.create_table(
            SCAN_TABLE,
            hash_key=("pk", "S"),
            range_key=("sk", "S"),
            wait=True,
        )
    yield dynamo
    # Cleanup: delete all items after test
    items = list(dynamo.scan(SCAN_TABLE))
    for item in items:
        dynamo.delete_item(SCAN_TABLE, {"pk": item["pk"], "sk": item["sk"]})


@pytest.fixture
def user_model(scan_table):
    """Create a User model for testing."""
    set_default_client(scan_table)

    class User(Model):
        model_config = ModelConfig(table=SCAN_TABLE)
        pk = StringAttribute(hash_key=True)
        sk = StringAttribute(range_key=True)
        name = StringAttribute()
        age = NumberAttribute()
        status = StringAttribute()

    User._client_instance = None
    return User


@pytest.fixture
def populated_users(scan_table, user_model):
    """Create test data for scan tests."""
    items = [
        {"pk": "USER#1", "sk": "PROFILE", "name": "Alice", "age": 25, "status": "active"},
        {"pk": "USER#2", "sk": "PROFILE", "name": "Bob", "age": 30, "status": "active"},
        {"pk": "USER#3", "sk": "PROFILE", "name": "Charlie", "age": 17, "status": "inactive"},
        {"pk": "USER#4", "sk": "PROFILE", "name": "Diana", "age": 22, "status": "active"},
        {"pk": "USER#5", "sk": "PROFILE", "name": "Eve", "age": 35, "status": "inactive"},
    ]
    for item in items:
        scan_table.put_item(SCAN_TABLE, item)
    return user_model


def test_model_scan_all_items(populated_users):
    """Test Model.scan returns all items."""
    User = populated_users

    users = list(User.scan())

    assert len(users) == 5
    for user in users:
        assert isinstance(user, User)


def test_model_scan_with_filter(populated_users):
    """Test Model.scan with filter_condition."""
    User = populated_users

    users = list(User.scan(filter_condition=User.status == "active"))

    assert len(users) == 3
    for user in users:
        assert user.status == "active"


def test_model_scan_with_numeric_filter(populated_users):
    """Test Model.scan with numeric filter."""
    User = populated_users

    users = list(User.scan(filter_condition=User.age >= 25))

    assert len(users) == 3
    for user in users:
        assert user.age >= 25


def test_model_scan_with_complex_filter(populated_users):
    """Test Model.scan with complex filter condition."""
    User = populated_users

    users = list(User.scan(filter_condition=(User.status == "active") & (User.age >= 25)))

    assert len(users) == 2
    for user in users:
        assert user.status == "active"
        assert user.age >= 25


def test_model_scan_first(populated_users):
    """Test Model.scan().first() returns first result."""
    User = populated_users

    user = User.scan().first()

    assert user is not None
    assert isinstance(user, User)


def test_model_scan_first_with_filter(populated_users):
    """Test Model.scan().first() with filter."""
    User = populated_users

    user = User.scan(filter_condition=User.name == "Alice").first()

    assert user is not None
    assert user.name == "Alice"


def test_model_scan_first_empty(populated_users):
    """Test Model.scan().first() returns None when no results."""
    User = populated_users

    user = User.scan(filter_condition=User.name == "NONEXISTENT").first()

    assert user is None


def test_model_scan_iteration(populated_users):
    """Test Model.scan can be iterated with for loop."""
    User = populated_users

    count = 0
    for user in User.scan():
        assert isinstance(user, User)
        count += 1

    assert count == 5


def test_model_scan_empty_result(scan_table, user_model):
    """Test Model.scan with no items in table."""

    # Create a model pointing to a different table
    class EmptyUser(Model):
        model_config = ModelConfig(table="empty_test_table")
        pk = StringAttribute(hash_key=True)
        sk = StringAttribute(range_key=True)

    EmptyUser._client_instance = None

    # Create the empty table
    scan_table.create_table(
        "empty_test_table",
        hash_key=("pk", "S"),
        range_key=("sk", "S"),
    )

    users = list(EmptyUser.scan())

    assert users == []

    # Cleanup
    scan_table.delete_table("empty_test_table")


def test_model_scan_last_evaluated_key(populated_users):
    """Test Model.scan exposes last_evaluated_key."""
    User = populated_users

    result = User.scan()

    # None before iteration
    assert result.last_evaluated_key is None

    # iterate all
    _ = list(result)

    # None after consuming all (no more pages)
    assert result.last_evaluated_key is None


def test_model_scan_consistent_read(populated_users):
    """Test Model.scan with consistent_read=True."""
    User = populated_users

    users = list(User.scan(consistent_read=True))

    assert len(users) == 5


def test_model_scan_with_limit(populated_users):
    """Test Model.scan with limit (auto-paginates)."""
    User = populated_users

    # limit is per page, but iterator fetches all
    users = list(User.scan(limit=2))

    assert len(users) == 5


# ========== COUNT TESTS ==========


def test_model_count_all(populated_users):
    """Test Model.count returns total count."""
    User = populated_users

    count, metrics = User.count()

    assert count == 5
    assert metrics is not None
    assert metrics.duration_ms > 0


def test_model_count_with_filter(populated_users):
    """Test Model.count with filter_condition."""
    User = populated_users

    count, _ = User.count(filter_condition=User.status == "active")

    assert count == 3


def test_model_count_with_numeric_filter(populated_users):
    """Test Model.count with numeric filter."""
    User = populated_users

    count, _ = User.count(filter_condition=User.age >= 25)

    assert count == 3


def test_model_count_with_complex_filter(populated_users):
    """Test Model.count with complex filter."""
    User = populated_users

    count, _ = User.count(filter_condition=(User.status == "active") & (User.age >= 25))

    assert count == 2


def test_model_count_empty_table(scan_table, user_model):
    """Test Model.count on empty table."""

    # Create a model pointing to a different table
    class EmptyUser(Model):
        model_config = ModelConfig(table="empty_count_table")
        pk = StringAttribute(hash_key=True)
        sk = StringAttribute(range_key=True)

    EmptyUser._client_instance = None

    # Create the empty table
    scan_table.create_table(
        "empty_count_table",
        hash_key=("pk", "S"),
        range_key=("sk", "S"),
    )

    count, _ = EmptyUser.count()

    assert count == 0

    # Cleanup
    scan_table.delete_table("empty_count_table")


def test_model_count_no_matches(populated_users):
    """Test Model.count when filter matches nothing."""
    User = populated_users

    count, _ = User.count(filter_condition=User.name == "NONEXISTENT")

    assert count == 0


def test_model_count_consistent_read(populated_users):
    """Test Model.count with consistent_read=True."""
    User = populated_users

    count, _ = User.count(consistent_read=True)

    assert count == 5


# ========== as_dict tests ==========


def test_model_scan_as_dict_returns_dicts(populated_users):
    """Test Model.scan(as_dict=True) returns plain dicts."""
    User = populated_users

    users = list(User.scan(as_dict=True))

    assert len(users) == 5
    for user in users:
        assert isinstance(user, dict)
        assert "pk" in user
        assert "name" in user


def test_model_scan_as_dict_false_returns_models(populated_users):
    """Test Model.scan(as_dict=False) returns Model instances."""
    User = populated_users

    users = list(User.scan(as_dict=False))

    assert len(users) == 5
    for user in users:
        assert isinstance(user, User)


def test_model_scan_as_dict_with_filter(populated_users):
    """Test Model.scan(as_dict=True) works with filter_condition."""
    User = populated_users

    users = list(User.scan(filter_condition=User.status == "active", as_dict=True))

    assert len(users) == 3
    for user in users:
        assert isinstance(user, dict)
        assert user["status"] == "active"


def test_model_scan_as_dict_first(populated_users):
    """Test Model.scan(as_dict=True).first() returns dict."""
    User = populated_users

    user = User.scan(as_dict=True).first()

    assert user is not None
    assert isinstance(user, dict)
