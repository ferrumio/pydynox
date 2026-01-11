"""Testing query operations with pydynox_memory_backend."""

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
    Order(pk="CUSTOMER#1", sk="ORDER#001", status="pending", total=100).save()
    Order(pk="CUSTOMER#1", sk="ORDER#002", status="shipped", total=200).save()
    Order(pk="CUSTOMER#2", sk="ORDER#001", status="pending", total=50).save()

    results = list(Order.query(hash_key="CUSTOMER#1"))

    assert len(results) == 2
    assert all(r.pk == "CUSTOMER#1" for r in results)


def test_query_with_range_key_condition(pydynox_memory_backend):
    """Test query with range key condition."""
    Order(pk="CUSTOMER#1", sk="ORDER#001", status="pending", total=100).save()
    Order(pk="CUSTOMER#1", sk="ORDER#002", status="shipped", total=200).save()
    Order(pk="CUSTOMER#1", sk="RETURN#001", status="pending", total=50).save()

    results = list(
        Order.query(
            hash_key="CUSTOMER#1",
            range_key_condition=Order.sk.begins_with("ORDER#"),
        )
    )

    assert len(results) == 2


def test_query_with_filter(pydynox_memory_backend):
    """Test query with filter condition."""
    Order(pk="CUSTOMER#1", sk="ORDER#001", status="pending", total=100).save()
    Order(pk="CUSTOMER#1", sk="ORDER#002", status="shipped", total=200).save()
    Order(pk="CUSTOMER#1", sk="ORDER#003", status="pending", total=300).save()

    results = list(
        Order.query(
            hash_key="CUSTOMER#1",
            filter_condition=Attr("status").eq("pending"),
        )
    )

    assert len(results) == 2
    assert all(r.status == "pending" for r in results)
