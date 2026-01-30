"""Async integration tests for template keys in single-table design."""

import pytest
from pydynox import DynamoDBClient, Model, ModelConfig, set_default_client
from pydynox.attributes import StringAttribute
from pydynox.indexes import GlobalSecondaryIndex


@pytest.fixture
def single_table_client(dynamodb_endpoint):
    """Create a pydynox client and table for single-table testing."""
    client = DynamoDBClient(
        region="us-east-1",
        endpoint_url=dynamodb_endpoint,
        access_key="testing",
        secret_key="testing",
    )

    # Delete if exists
    if client.sync_table_exists("single_table_async_test"):
        client.sync_delete_table("single_table_async_test")

    # Create table with inverted GSI
    client.sync_create_table(
        "single_table_async_test",
        partition_key=("pk", "S"),
        sort_key=("sk", "S"),
        global_secondary_indexes=[
            {
                "index_name": "inverted",
                "hash_key": ("sk", "S"),
                "range_key": ("pk", "S"),
                "projection": "ALL",
            },
        ],
    )

    set_default_client(client)
    return client


@pytest.mark.asyncio
async def test_user_order_single_table(single_table_client):
    """Test User/Order single-table pattern with inverted index."""

    class UserOrder(Model):
        model_config = ModelConfig(table="single_table_async_test")
        pk = StringAttribute(partition_key=True, template="USER#{user_id}")
        sk = StringAttribute(sort_key=True, template="ORDER#{order_id}")
        user_id = StringAttribute()
        order_id = StringAttribute()
        status = StringAttribute()

        by_order = GlobalSecondaryIndex(
            index_name="inverted",
            partition_key="sk",
            sort_key="pk",
        )

    # GIVEN orders for multiple users
    await UserOrder(user_id="alice", order_id="001", status="shipped").save()
    await UserOrder(user_id="alice", order_id="002", status="pending").save()
    await UserOrder(user_id="bob", order_id="003", status="shipped").save()

    # WHEN querying main table by user_id (template placeholder)
    alice_orders = [o async for o in UserOrder.query(user_id="alice")]

    # THEN should return alice's orders
    assert len(alice_orders) == 2

    # WHEN querying inverted index by order_id (template placeholder)
    order_003 = [o async for o in UserOrder.by_order.query(order_id="003")]

    # THEN should return the order with user info
    assert len(order_003) == 1
    assert order_003[0].user_id == "bob"


@pytest.mark.asyncio
async def test_follower_following_pattern(single_table_client):
    """Test social follow pattern with inverted index."""

    class Follow(Model):
        model_config = ModelConfig(table="single_table_async_test")
        pk = StringAttribute(partition_key=True, template="FOLLOWER#{follower}")
        sk = StringAttribute(sort_key=True, template="FOLLOWING#{following}")
        follower = StringAttribute()
        following = StringAttribute()

        followers_index = GlobalSecondaryIndex(
            index_name="inverted",
            partition_key="sk",
            sort_key="pk",
        )

    # GIVEN alice follows bob and charlie, dave follows bob
    await Follow(follower="alice", following="bob").save()
    await Follow(follower="alice", following="charlie").save()
    await Follow(follower="dave", following="bob").save()

    # WHEN querying who alice follows (main table)
    alice_following = [f async for f in Follow.query(follower="alice")]

    # THEN should return bob and charlie
    assert len(alice_following) == 2
    assert {f.following for f in alice_following} == {"bob", "charlie"}

    # WHEN querying who follows bob (inverted index)
    bob_followers = [f async for f in Follow.followers_index.query(following="bob")]

    # THEN should return alice and dave
    assert len(bob_followers) == 2
    assert {f.follower for f in bob_followers} == {"alice", "dave"}


@pytest.mark.asyncio
async def test_user_profile_static_sk(single_table_client):
    """Test user with static sort key."""

    class User(Model):
        model_config = ModelConfig(table="single_table_async_test")
        pk = StringAttribute(partition_key=True, template="USER#{email}")
        sk = StringAttribute(sort_key=True, template="PROFILE")
        email = StringAttribute()
        name = StringAttribute()

    # GIVEN a user with template keys
    await User(email="john@example.com", name="John Doe").save()

    # WHEN getting by built key
    found = await User.get(pk="USER#john@example.com", sk="PROFILE")

    # THEN should return the user
    assert found is not None
    assert found.email == "john@example.com"
    assert found.name == "John Doe"


@pytest.mark.asyncio
async def test_multiple_placeholders(single_table_client):
    """Test template with multiple placeholders."""

    class Event(Model):
        model_config = ModelConfig(table="single_table_async_test")
        pk = StringAttribute(partition_key=True, template="TENANT#{tenant_id}")
        sk = StringAttribute(sort_key=True, template="EVENT#{date}#{event_id}")
        tenant_id = StringAttribute()
        date = StringAttribute()
        event_id = StringAttribute()
        data = StringAttribute()

    # GIVEN events with multiple placeholders in sk
    await Event(tenant_id="acme", date="2024-01-15", event_id="e1", data="login").save()
    await Event(tenant_id="acme", date="2024-01-15", event_id="e2", data="purchase").save()
    await Event(tenant_id="acme", date="2024-01-16", event_id="e3", data="logout").save()

    # WHEN querying by tenant_id (template placeholder)
    events = [e async for e in Event.query(tenant_id="acme")]

    # THEN should return all events with correctly built sk
    assert len(events) == 3
    assert events[0].sk.startswith("EVENT#2024-01-15#")


@pytest.mark.asyncio
async def test_direct_key_still_works(single_table_client):
    """Test that direct partition_key still works alongside template."""

    class Order(Model):
        model_config = ModelConfig(table="single_table_async_test")
        pk = StringAttribute(partition_key=True, template="USER#{user_id}")
        sk = StringAttribute(sort_key=True, template="ORDER#{order_id}")
        user_id = StringAttribute()
        order_id = StringAttribute()

    # GIVEN orders with template keys
    await Order(user_id="123", order_id="A").save()
    await Order(user_id="123", order_id="B").save()

    # WHEN querying with template placeholder
    orders1 = [o async for o in Order.query(user_id="123")]

    # THEN should return orders
    assert len(orders1) == 2

    # WHEN querying with direct partition_key (already built)
    orders2 = [o async for o in Order.query(partition_key="USER#123")]

    # THEN should return same results
    assert len(orders2) == 2
    assert {o.order_id for o in orders1} == {o.order_id for o in orders2}


@pytest.mark.asyncio
async def test_inverted_index_query_with_direct_sk(single_table_client):
    """Test inverted index query using direct sk value instead of placeholder."""

    class UserOrder(Model):
        model_config = ModelConfig(table="single_table_async_test")
        pk = StringAttribute(partition_key=True, template="USER#{user_id}")
        sk = StringAttribute(sort_key=True, template="ORDER#{order_id}")
        user_id = StringAttribute()
        order_id = StringAttribute()

        by_order = GlobalSecondaryIndex(
            index_name="inverted",
            partition_key="sk",
            sort_key="pk",
        )

    # GIVEN an order
    await UserOrder(user_id="alice", order_id="X1").save()

    # WHEN querying with direct sk value (already built)
    results = [o async for o in UserOrder.by_order.query(sk="ORDER#X1")]

    # THEN should return the order
    assert len(results) == 1
    assert results[0].user_id == "alice"


@pytest.mark.asyncio
async def test_inverted_index_with_sort_key_condition(single_table_client):
    """Test inverted index query with range key condition on pk."""

    class UserOrder(Model):
        model_config = ModelConfig(table="single_table_async_test")
        pk = StringAttribute(partition_key=True, template="USER#{user_id}")
        sk = StringAttribute(sort_key=True, template="ORDER#{order_id}")
        user_id = StringAttribute()
        order_id = StringAttribute()

        by_order = GlobalSecondaryIndex(
            index_name="inverted",
            partition_key="sk",
            sort_key="pk",
        )

    # GIVEN same order from different users
    await UserOrder(user_id="alice", order_id="SHARED").save()
    await UserOrder(user_id="bob", order_id="SHARED").save()
    await UserOrder(user_id="charlie", order_id="SHARED").save()

    # WHEN querying with range key condition on pk
    results = [
        o
        async for o in UserOrder.by_order.query(
            order_id="SHARED",
            sort_key_condition=UserOrder.pk.begins_with("USER#a"),
        )
    ]

    # THEN should return only alice's order
    assert len(results) == 1
    assert results[0].user_id == "alice"


@pytest.mark.asyncio
async def test_inverted_index_with_filter_condition(single_table_client):
    """Test inverted index query with filter condition."""

    class UserOrder(Model):
        model_config = ModelConfig(table="single_table_async_test")
        pk = StringAttribute(partition_key=True, template="USER#{user_id}")
        sk = StringAttribute(sort_key=True, template="ORDER#{order_id}")
        user_id = StringAttribute()
        order_id = StringAttribute()
        status = StringAttribute()

        by_order = GlobalSecondaryIndex(
            index_name="inverted",
            partition_key="sk",
            sort_key="pk",
        )

    # GIVEN orders with different statuses
    await UserOrder(user_id="alice", order_id="MULTI", status="shipped").save()
    await UserOrder(user_id="bob", order_id="MULTI", status="pending").save()

    # WHEN querying with filter condition
    results = [
        o
        async for o in UserOrder.by_order.query(
            order_id="MULTI",
            filter_condition=UserOrder.status == "shipped",
        )
    ]

    # THEN should return only shipped order
    assert len(results) == 1
    assert results[0].user_id == "alice"


@pytest.mark.asyncio
async def test_mixed_entity_types_single_table(single_table_client):
    """Test multiple entity types in same table with different templates."""

    class User(Model):
        model_config = ModelConfig(table="single_table_async_test")
        pk = StringAttribute(partition_key=True, template="USER#{user_id}")
        sk = StringAttribute(sort_key=True, template="PROFILE")
        user_id = StringAttribute()
        name = StringAttribute()

    class Order(Model):
        model_config = ModelConfig(table="single_table_async_test")
        pk = StringAttribute(partition_key=True, template="USER#{user_id}")
        sk = StringAttribute(sort_key=True, template="ORDER#{order_id}")
        user_id = StringAttribute()
        order_id = StringAttribute()
        total = StringAttribute()

    # GIVEN user and orders in same table
    await User(user_id="alice", name="Alice").save()
    await Order(user_id="alice", order_id="001", total="100").save()
    await Order(user_id="alice", order_id="002", total="200").save()

    # WHEN getting user profile
    user = await User.get(pk="USER#alice", sk="PROFILE")

    # THEN should return user
    assert user is not None
    assert user.name == "Alice"

    # WHEN querying orders with sk prefix filter
    orders = [
        o
        async for o in Order.query(
            user_id="alice",
            sort_key_condition=Order.sk.begins_with("ORDER#"),
        )
    ]

    # THEN should return only orders, not profile
    assert len(orders) == 2
