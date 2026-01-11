"""Testing scan operations with pydynox_memory_backend."""

from pydynox import Model, ModelConfig
from pydynox.attributes import NumberAttribute, StringAttribute
from pydynox.conditions import Attr


class User(Model):
    model_config = ModelConfig(table="users")
    pk = StringAttribute(hash_key=True)
    name = StringAttribute()
    age = NumberAttribute()
    status = StringAttribute(default="active")


def test_scan_all_items(pydynox_memory_backend):
    """Test scanning all items in a table."""
    User(pk="USER#1", name="Alice", age=30).save()
    User(pk="USER#2", name="Bob", age=25).save()
    User(pk="USER#3", name="Charlie", age=35).save()

    results = list(User.scan())

    assert len(results) == 3


def test_scan_with_filter(pydynox_memory_backend):
    """Test scan with filter condition."""
    User(pk="USER#1", name="Alice", age=30, status="active").save()
    User(pk="USER#2", name="Bob", age=25, status="inactive").save()
    User(pk="USER#3", name="Charlie", age=35, status="active").save()

    results = list(User.scan(filter_condition=Attr("status").eq("active")))

    assert len(results) == 2
    assert all(r.status == "active" for r in results)


def test_scan_with_numeric_filter(pydynox_memory_backend):
    """Test scan with numeric filter."""
    User(pk="USER#1", name="Alice", age=30).save()
    User(pk="USER#2", name="Bob", age=25).save()
    User(pk="USER#3", name="Charlie", age=35).save()

    results = list(User.scan(filter_condition=Attr("age").gt(28)))

    assert len(results) == 2


def test_count_items(pydynox_memory_backend):
    """Test counting items."""
    User(pk="USER#1", name="Alice", age=30).save()
    User(pk="USER#2", name="Bob", age=25).save()
    User(pk="USER#3", name="Charlie", age=35).save()

    count, _ = User.count()

    assert count == 3
