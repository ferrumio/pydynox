"""Testing query and scan operations."""

from pydynox import Model, ModelConfig
from pydynox.attributes import NumberAttribute, StringAttribute
from pydynox.conditions import Attr


class Order(Model):
    model_config = ModelConfig(table="orders")
    pk = StringAttribute(hash_key=True)
    sk = StringAttribute(range_key=True)
    status = StringAttribute()
    total = NumberAttribute()


def test_query_by_hash_key(pydynox_memory_backend):
    """Test querying items by partition key."""
    Order(pk="USER#1", sk="ORDER#001", status="pending", total=100).save()
    Order(pk="USER#1", sk="ORDER#002", status="shipped", total=200).save()
    Order(pk="USER#2", sk="ORDER#001", status="pending", total=50).save()

    # Query returns only USER#1's orders
    results = list(Order.query(hash_key="USER#1"))
    assert len(results) == 2


def test_query_with_filter(pydynox_memory_backend):
    """Test query with filter condition."""
    Order(pk="USER#1", sk="ORDER#001", status="pending", total=100).save()
    Order(pk="USER#1", sk="ORDER#002", status="shipped", total=200).save()
    Order(pk="USER#1", sk="ORDER#003", status="pending", total=300).save()

    # Filter by status
    results = list(
        Order.query(
            hash_key="USER#1",
            filter_condition=Attr("status").eq("pending"),
        )
    )
    assert len(results) == 2


def test_scan_all_items(pydynox_memory_backend):
    """Test scanning all items in a table."""
    Order(pk="USER#1", sk="ORDER#001", status="pending", total=100).save()
    Order(pk="USER#2", sk="ORDER#001", status="shipped", total=200).save()
    Order(pk="USER#3", sk="ORDER#001", status="pending", total=300).save()

    results = list(Order.scan())
    assert len(results) == 3


def test_scan_with_filter(pydynox_memory_backend):
    """Test scan with filter condition."""
    Order(pk="USER#1", sk="ORDER#001", status="pending", total=100).save()
    Order(pk="USER#2", sk="ORDER#001", status="shipped", total=200).save()
    Order(pk="USER#3", sk="ORDER#001", status="pending", total=300).save()

    # Filter by total > 150
    results = list(Order.scan(filter_condition=Attr("total").gt(150)))
    assert len(results) == 2
