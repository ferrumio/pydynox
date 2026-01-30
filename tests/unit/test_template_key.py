"""Tests for StringAttribute template feature."""

import pytest
from pydynox import Model, ModelConfig
from pydynox.attributes import StringAttribute
from pydynox.testing import MemoryBackend


def test_parse_simple_template():
    """Test parsing a simple template."""
    attr = StringAttribute(partition_key=True, template="USER#{email}")
    assert attr.has_template
    assert attr.placeholders == ["email"]
    assert attr.get_prefix() == "USER#"


def test_parse_multiple_placeholders():
    """Test parsing template with multiple placeholders."""
    attr = StringAttribute(sort_key=True, template="ORDER#{order_id}#{created_at}")
    assert attr.placeholders == ["order_id", "created_at"]
    assert attr.get_prefix() == "ORDER#"


def test_parse_static_template():
    """Test parsing template with no placeholders."""
    attr = StringAttribute(sort_key=True, template="PROFILE")
    assert attr.placeholders == []
    assert attr.get_prefix() == "PROFILE"


def test_build_key_simple():
    """Test building key from simple template."""
    attr = StringAttribute(partition_key=True, template="USER#{email}")
    key = attr.build_key({"email": "john@example.com"})
    assert key == "USER#john@example.com"


def test_build_key_multiple_placeholders():
    """Test building key with multiple placeholders."""
    attr = StringAttribute(sort_key=True, template="ORDER#{order_id}#{date}")
    key = attr.build_key({"order_id": "123", "date": "2024-01-01"})
    assert key == "ORDER#123#2024-01-01"


def test_build_key_missing_placeholder():
    """Test error when placeholder value is missing."""
    attr = StringAttribute(partition_key=True, template="USER#{email}")
    with pytest.raises(ValueError, match="Missing value for template placeholder"):
        attr.build_key({})


def test_no_template():
    """Test attribute without template."""
    attr = StringAttribute(partition_key=True)
    assert not attr.has_template
    assert attr.placeholders == []
    assert attr.get_prefix() == ""


def test_model_with_template():
    """Test Model with template keys."""

    class User(Model):
        model_config = ModelConfig(table="test")
        pk = StringAttribute(partition_key=True, template="USER#{email}")
        sk = StringAttribute(sort_key=True, template="PROFILE")
        email = StringAttribute()
        name = StringAttribute()

    user = User(email="john@example.com", name="John")
    assert user.pk == "USER#john@example.com"
    assert user.sk == "PROFILE"
    assert user.email == "john@example.com"
    assert user.name == "John"


def test_model_with_multiple_placeholders():
    """Test Model with multiple placeholders in template."""

    class Order(Model):
        model_config = ModelConfig(table="test")
        pk = StringAttribute(partition_key=True, template="USER#{user_id}")
        sk = StringAttribute(sort_key=True, template="ORDER#{order_id}#{date}")
        user_id = StringAttribute()
        order_id = StringAttribute()
        date = StringAttribute()
        status = StringAttribute()

    order = Order(user_id="123", order_id="456", date="2024-01-01", status="pending")
    assert order.pk == "USER#123"
    assert order.sk == "ORDER#456#2024-01-01"


def test_model_to_dict():
    """Test that to_dict includes built keys."""

    class User(Model):
        model_config = ModelConfig(table="test")
        pk = StringAttribute(partition_key=True, template="USER#{email}")
        sk = StringAttribute(sort_key=True, template="PROFILE")
        email = StringAttribute()
        name = StringAttribute()

    user = User(email="john@example.com", name="John")
    data = user.to_dict()

    assert data["pk"] == "USER#john@example.com"
    assert data["sk"] == "PROFILE"
    assert data["email"] == "john@example.com"
    assert data["name"] == "John"


def test_model_from_dict():
    """Test that from_dict works with template keys."""

    class User(Model):
        model_config = ModelConfig(table="test")
        pk = StringAttribute(partition_key=True, template="USER#{email}")
        sk = StringAttribute(sort_key=True, template="PROFILE")
        email = StringAttribute()
        name = StringAttribute()

    data = {
        "pk": "USER#john@example.com",
        "sk": "PROFILE",
        "email": "john@example.com",
        "name": "John",
    }
    user = User.from_dict(data)

    assert user.pk == "USER#john@example.com"
    assert user.sk == "PROFILE"
    assert user.email == "john@example.com"


@MemoryBackend()
def test_model_save_and_get():
    """Test saving and getting model with template keys."""

    class User(Model):
        model_config = ModelConfig(table="users")
        pk = StringAttribute(partition_key=True, template="USER#{email}")
        sk = StringAttribute(sort_key=True, template="PROFILE")
        email = StringAttribute()
        name = StringAttribute()

    # Save
    user = User(email="john@example.com", name="John")
    user.sync_save()

    # Get by built key
    found = User.sync_get(pk="USER#john@example.com", sk="PROFILE")
    assert found is not None
    assert found.email == "john@example.com"
    assert found.name == "John"


@MemoryBackend()
def test_model_query_with_template():
    """Test querying model with template keys."""

    class Order(Model):
        model_config = ModelConfig(table="orders")
        pk = StringAttribute(partition_key=True, template="USER#{user_id}")
        sk = StringAttribute(sort_key=True, template="ORDER#{order_id}")
        user_id = StringAttribute()
        order_id = StringAttribute()
        status = StringAttribute()

    # Save some orders
    Order(user_id="123", order_id="A", status="pending").sync_save()
    Order(user_id="123", order_id="B", status="shipped").sync_save()
    Order(user_id="456", order_id="C", status="pending").sync_save()

    # Query by built pk
    orders = list(Order.sync_query(partition_key="USER#123"))
    assert len(orders) == 2
    assert all(o.user_id == "123" for o in orders)


@MemoryBackend()
def test_model_query_with_template_placeholder():
    """Test querying using template placeholder instead of partition_key."""

    class Order(Model):
        model_config = ModelConfig(table="orders")
        pk = StringAttribute(partition_key=True, template="USER#{user_id}")
        sk = StringAttribute(sort_key=True, template="ORDER#{order_id}")
        user_id = StringAttribute()
        order_id = StringAttribute()
        status = StringAttribute()

    # Save some orders
    Order(user_id="123", order_id="A", status="pending").sync_save()
    Order(user_id="123", order_id="B", status="shipped").sync_save()
    Order(user_id="456", order_id="C", status="pending").sync_save()

    # Query using template placeholder
    orders = list(Order.sync_query(user_id="123"))
    assert len(orders) == 2
    assert all(o.user_id == "123" for o in orders)


@MemoryBackend()
def test_model_query_without_template_requires_partition_key():
    """Test that query without template requires partition_key."""

    class Item(Model):
        model_config = ModelConfig(table="items")
        pk = StringAttribute(partition_key=True)  # No template
        name = StringAttribute()

    Item(pk="ITEM#1", name="Test").sync_save()

    # Should work with partition_key
    items = list(Item.sync_query(partition_key="ITEM#1"))
    assert len(items) == 1

    # Should fail without partition_key (no template to build from)
    with pytest.raises(ValueError, match="partition_key is required"):
        list(Item.sync_query())


# ========== INVERTED INDEX TESTS ==========


@MemoryBackend()
def test_inverted_index_with_template():
    """Test inverted index (GSI where pk/sk are swapped) with templates."""
    from pydynox.indexes import GlobalSecondaryIndex

    class UserOrder(Model):
        """Access pattern: User -> Orders and Order -> User"""

        model_config = ModelConfig(table="app")

        # Main table: pk=USER#123, sk=ORDER#456
        pk = StringAttribute(partition_key=True, template="USER#{user_id}")
        sk = StringAttribute(sort_key=True, template="ORDER#{order_id}")

        user_id = StringAttribute()
        order_id = StringAttribute()
        status = StringAttribute()

        # Inverted index: pk=ORDER#456, sk=USER#123
        inverted_index = GlobalSecondaryIndex(
            index_name="inverted",
            partition_key="sk",  # ORDER#456 becomes pk
            sort_key="pk",  # USER#123 becomes sk
        )

    # Create orders
    UserOrder(user_id="123", order_id="A", status="pending").sync_save()
    UserOrder(user_id="123", order_id="B", status="shipped").sync_save()
    UserOrder(user_id="456", order_id="C", status="pending").sync_save()

    # Query main table by user_id (using template)
    orders = list(UserOrder.sync_query(user_id="123"))
    assert len(orders) == 2
    assert all(o.user_id == "123" for o in orders)

    # Query inverted index by order_id (using template placeholder)
    # This should build sk="ORDER#A" from order_id="A"
    results = list(UserOrder.inverted_index.sync_query(order_id="A"))
    assert len(results) == 1
    assert results[0].order_id == "A"
    assert results[0].user_id == "123"


@MemoryBackend()
def test_inverted_index_direct_key():
    """Test inverted index with direct key value (no template resolution)."""
    from pydynox.indexes import GlobalSecondaryIndex

    class UserOrder(Model):
        model_config = ModelConfig(table="app")
        pk = StringAttribute(partition_key=True, template="USER#{user_id}")
        sk = StringAttribute(sort_key=True, template="ORDER#{order_id}")
        user_id = StringAttribute()
        order_id = StringAttribute()
        status = StringAttribute()

        inverted_index = GlobalSecondaryIndex(
            index_name="inverted",
            partition_key="sk",
            sort_key="pk",
        )

    UserOrder(user_id="123", order_id="A", status="pending").sync_save()

    # Query with direct sk value (already built)
    results = list(UserOrder.inverted_index.sync_query(sk="ORDER#A"))
    assert len(results) == 1
    assert results[0].order_id == "A"


@MemoryBackend()
def test_follow_relationship_inverted_index():
    """Test follower/following pattern with inverted index."""
    from pydynox.indexes import GlobalSecondaryIndex

    class Follow(Model):
        """User A follows User B"""

        model_config = ModelConfig(table="social")

        # Main: pk=FOLLOWER#alice, sk=FOLLOWING#bob
        pk = StringAttribute(partition_key=True, template="FOLLOWER#{follower_id}")
        sk = StringAttribute(sort_key=True, template="FOLLOWING#{following_id}")

        follower_id = StringAttribute()
        following_id = StringAttribute()
        created_at = StringAttribute()

        # Inverted: pk=FOLLOWING#bob, sk=FOLLOWER#alice
        followers_index = GlobalSecondaryIndex(
            index_name="followers",
            partition_key="sk",
            sort_key="pk",
        )

    # Alice follows Bob and Charlie
    Follow(follower_id="alice", following_id="bob", created_at="2024-01-01").sync_save()
    Follow(follower_id="alice", following_id="charlie", created_at="2024-01-02").sync_save()
    # Dave follows Bob
    Follow(follower_id="dave", following_id="bob", created_at="2024-01-03").sync_save()

    # Who does Alice follow? (main table)
    following = list(Follow.sync_query(follower_id="alice"))
    assert len(following) == 2
    assert {f.following_id for f in following} == {"bob", "charlie"}

    # Who follows Bob? (inverted index)
    followers = list(Follow.followers_index.sync_query(following_id="bob"))
    assert len(followers) == 2
    assert {f.follower_id for f in followers} == {"alice", "dave"}


def test_gsi_template_resolution_error():
    """Test error when neither direct key nor template placeholders provided."""
    from pydynox.indexes import GlobalSecondaryIndex

    class UserOrder(Model):
        model_config = ModelConfig(table="app")
        pk = StringAttribute(partition_key=True, template="USER#{user_id}")
        sk = StringAttribute(sort_key=True, template="ORDER#{order_id}")
        user_id = StringAttribute()
        order_id = StringAttribute()

        inverted_index = GlobalSecondaryIndex(
            index_name="inverted",
            partition_key="sk",
        )

    # Should fail - neither sk nor order_id provided
    with pytest.raises(ValueError, match="GSI query requires 'sk' or its template placeholders"):
        list(UserOrder.inverted_index.sync_query(wrong_key="value"))
