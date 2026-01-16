"""Integration tests for Model.query() method."""

import pytest
from pydynox import Model, ModelConfig, set_default_client
from pydynox.attributes import NumberAttribute, StringAttribute


@pytest.fixture
def order_model(dynamo):
    """Create an Order model for testing."""
    set_default_client(dynamo)

    class Order(Model):
        model_config = ModelConfig(table="test_table")
        pk = StringAttribute(hash_key=True)
        sk = StringAttribute(range_key=True)
        total = NumberAttribute()
        status = StringAttribute()

    Order._client_instance = None
    return Order


@pytest.fixture
def populated_orders(dynamo, order_model):
    """Create test data for query tests."""
    items = [
        {"pk": "CUSTOMER#1", "sk": "ORDER#001", "total": 100, "status": "shipped"},
        {"pk": "CUSTOMER#1", "sk": "ORDER#002", "total": 200, "status": "pending"},
        {"pk": "CUSTOMER#1", "sk": "ORDER#003", "total": 50, "status": "shipped"},
        {"pk": "CUSTOMER#1", "sk": "PROFILE", "total": 0, "status": "active"},
        {"pk": "CUSTOMER#2", "sk": "ORDER#001", "total": 75, "status": "shipped"},
    ]
    for item in items:
        dynamo.put_item("test_table", item)
    return order_model


def test_model_query_by_hash_key(populated_orders):
    """Test Model.query returns typed instances."""
    Order = populated_orders

    # WHEN we query by hash key
    orders = list(Order.query(hash_key="CUSTOMER#1"))

    # THEN typed model instances are returned
    assert len(orders) == 4
    for order in orders:
        assert isinstance(order, Order)
        assert order.pk == "CUSTOMER#1"


def test_model_query_with_range_key_condition(populated_orders):
    """Test Model.query with range_key_condition."""
    Order = populated_orders

    orders = list(
        Order.query(
            hash_key="CUSTOMER#1",
            range_key_condition=Order.sk.begins_with("ORDER#"),
        )
    )

    assert len(orders) == 3
    for order in orders:
        assert order.sk.startswith("ORDER#")


def test_model_query_with_filter_condition(populated_orders):
    """Test Model.query with filter_condition."""
    Order = populated_orders

    # WHEN we query with filter condition
    orders = list(
        Order.query(
            hash_key="CUSTOMER#1",
            filter_condition=Order.status == "shipped",
        )
    )

    # THEN only matching items are returned
    assert len(orders) == 2
    for order in orders:
        assert order.status == "shipped"


def test_model_query_with_range_and_filter(populated_orders):
    """Test Model.query with both range_key_condition and filter_condition."""
    Order = populated_orders

    orders = list(
        Order.query(
            hash_key="CUSTOMER#1",
            range_key_condition=Order.sk.begins_with("ORDER#"),
            filter_condition=Order.total >= 100,
        )
    )

    assert len(orders) == 2
    for order in orders:
        assert order.sk.startswith("ORDER#")
        assert order.total >= 100


def test_model_query_descending_order(populated_orders):
    """Test Model.query with scan_index_forward=False."""
    Order = populated_orders

    asc_orders = list(
        Order.query(
            hash_key="CUSTOMER#1",
            range_key_condition=Order.sk.begins_with("ORDER#"),
            scan_index_forward=True,
        )
    )

    desc_orders = list(
        Order.query(
            hash_key="CUSTOMER#1",
            range_key_condition=Order.sk.begins_with("ORDER#"),
            scan_index_forward=False,
        )
    )

    asc_sks = [o.sk for o in asc_orders]
    desc_sks = [o.sk for o in desc_orders]

    assert asc_sks == list(reversed(desc_sks))


def test_model_query_with_limit(populated_orders):
    """Test Model.query with limit returns only N items total."""
    Order = populated_orders

    # GIVEN 4 items for CUSTOMER#1
    # WHEN we query with limit=2
    orders = list(
        Order.query(
            hash_key="CUSTOMER#1",
            limit=2,
        )
    )

    # THEN only 2 items are returned (limit stops iteration)
    assert len(orders) == 2


def test_model_query_first(populated_orders):
    """Test Model.query().first() returns first result."""
    Order = populated_orders

    order = Order.query(
        hash_key="CUSTOMER#1",
        range_key_condition=Order.sk.begins_with("ORDER#"),
    ).first()

    assert order is not None
    assert isinstance(order, Order)
    assert order.sk == "ORDER#001"


def test_model_query_first_empty(populated_orders):
    """Test Model.query().first() returns None when no results."""
    Order = populated_orders

    order = Order.query(hash_key="NONEXISTENT").first()

    assert order is None


def test_model_query_iteration(populated_orders):
    """Test Model.query can be iterated with for loop."""
    Order = populated_orders

    count = 0
    for order in Order.query(hash_key="CUSTOMER#1"):
        assert isinstance(order, Order)
        count += 1

    assert count == 4


def test_model_query_empty_result(populated_orders):
    """Test Model.query with no matching items."""
    Order = populated_orders

    orders = list(Order.query(hash_key="NONEXISTENT"))

    assert orders == []


def test_model_query_last_evaluated_key(populated_orders):
    """Test Model.query exposes last_evaluated_key."""
    Order = populated_orders

    result = Order.query(hash_key="CUSTOMER#1")

    # None before iteration
    assert result.last_evaluated_key is None

    # iterate all
    _ = list(result)

    # None after consuming all (no more pages)
    assert result.last_evaluated_key is None


def test_model_query_consistent_read(populated_orders):
    """Test Model.query with consistent_read=True."""
    Order = populated_orders

    orders = list(
        Order.query(
            hash_key="CUSTOMER#1",
            consistent_read=True,
        )
    )

    assert len(orders) == 4


def test_model_query_complex_filter(populated_orders):
    """Test Model.query with complex filter condition."""
    Order = populated_orders

    orders = list(
        Order.query(
            hash_key="CUSTOMER#1",
            range_key_condition=Order.sk.begins_with("ORDER#"),
            filter_condition=(Order.status == "shipped") & (Order.total > 50),
        )
    )

    assert len(orders) == 1
    assert orders[0].total == 100
    assert orders[0].status == "shipped"


# ========== as_dict tests ==========


def test_model_query_as_dict_returns_dicts(populated_orders):
    """Test Model.query(as_dict=True) returns plain dicts."""
    Order = populated_orders

    orders = list(Order.query(hash_key="CUSTOMER#1", as_dict=True))

    assert len(orders) == 4
    for order in orders:
        assert isinstance(order, dict)
        assert order["pk"] == "CUSTOMER#1"


def test_model_query_as_dict_false_returns_models(populated_orders):
    """Test Model.query(as_dict=False) returns Model instances."""
    Order = populated_orders

    orders = list(Order.query(hash_key="CUSTOMER#1", as_dict=False))

    assert len(orders) == 4
    for order in orders:
        assert isinstance(order, Order)


def test_model_query_as_dict_with_filter(populated_orders):
    """Test Model.query(as_dict=True) works with filter_condition."""
    Order = populated_orders

    orders = list(
        Order.query(
            hash_key="CUSTOMER#1",
            filter_condition=Order.status == "shipped",
            as_dict=True,
        )
    )

    assert len(orders) == 2
    for order in orders:
        assert isinstance(order, dict)
        assert order["status"] == "shipped"


def test_model_query_as_dict_first(populated_orders):
    """Test Model.query(as_dict=True).first() returns dict."""
    Order = populated_orders

    order = Order.query(
        hash_key="CUSTOMER#1",
        range_key_condition=Order.sk.begins_with("ORDER#"),
        as_dict=True,
    ).first()

    assert order is not None
    assert isinstance(order, dict)
    assert order["sk"] == "ORDER#001"
