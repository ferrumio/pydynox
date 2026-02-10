"""Sync integration tests for field alias feature.

Tests that aliases work end-to-end with real DynamoDB (LocalStack).
Python names are used in code, short alias names are stored in DynamoDB.
"""

import uuid

import pytest
from pydynox import DynamoDBClient, Model, ModelConfig, set_default_client
from pydynox.attributes import NumberAttribute, StringAttribute


class Product(Model):
    model_config = ModelConfig(table="test_table")
    pk = StringAttribute(partition_key=True)
    sk = StringAttribute(sort_key=True)
    product_name = StringAttribute(alias="pn")
    price = NumberAttribute(alias="pr")
    quantity = NumberAttribute(alias="q")


class Thing(Model):
    model_config = ModelConfig(table="test_table")
    partition = StringAttribute(partition_key=True, alias="pk")
    sort = StringAttribute(sort_key=True, alias="sk")
    data = StringAttribute(alias="d")


@pytest.fixture
def table(dynamo: DynamoDBClient):
    """Set default client for all tests."""
    set_default_client(dynamo)
    yield dynamo


def test_sync_save_and_get_with_alias(table):
    """Save with Python names, get back with Python names."""
    uid = str(uuid.uuid4())[:8]
    product = Product(
        pk=f"ALIAS#{uid}", sk="PRODUCT#1", product_name="Laptop", price=999, quantity=5
    )
    product.sync_save()

    loaded = Product.sync_get(pk=f"ALIAS#{uid}", sk="PRODUCT#1")
    assert loaded is not None
    assert loaded.product_name == "Laptop"
    assert loaded.price == 999
    assert loaded.quantity == 5


def test_sync_alias_stored_as_short_names(table):
    """Verify DynamoDB stores the alias names, not Python names."""
    uid = str(uuid.uuid4())[:8]
    product = Product(
        pk=f"ALIAS_RAW#{uid}", sk="PRODUCT#1", product_name="Mouse", price=25, quantity=100
    )
    product.sync_save()

    # Read raw item from DynamoDB (bypassing Model)
    raw = table.sync_get_item("test_table", {"pk": f"ALIAS_RAW#{uid}", "sk": "PRODUCT#1"})
    assert raw is not None
    # Alias names should be in the raw item
    assert raw["pn"] == "Mouse"
    assert raw["pr"] == 25
    assert raw["q"] == 100
    # Python names should NOT be in the raw item
    assert "product_name" not in raw
    assert "price" not in raw
    assert "quantity" not in raw


def test_sync_update_with_alias(table):
    """Update aliased fields by Python name."""
    uid = str(uuid.uuid4())[:8]
    product = Product(
        pk=f"ALIAS_UPD#{uid}", sk="PRODUCT#1", product_name="Keyboard", price=75, quantity=50
    )
    product.sync_save()

    product.sync_update(price=80)

    loaded = Product.sync_get(pk=f"ALIAS_UPD#{uid}", sk="PRODUCT#1")
    assert loaded is not None
    assert loaded.price == 80
    assert loaded.product_name == "Keyboard"


def test_sync_delete_with_alias(table):
    """Delete item that has aliased fields."""
    uid = str(uuid.uuid4())[:8]
    product = Product(
        pk=f"ALIAS_DEL#{uid}", sk="PRODUCT#1", product_name="Monitor", price=300, quantity=10
    )
    product.sync_save()

    product.sync_delete()

    loaded = Product.sync_get(pk=f"ALIAS_DEL#{uid}", sk="PRODUCT#1")
    assert loaded is None


def test_sync_condition_with_alias(table):
    """Conditions use alias names in DynamoDB expressions."""
    uid = str(uuid.uuid4())[:8]
    product = Product(
        pk=f"ALIAS_COND#{uid}", sk="PRODUCT#1", product_name="Cable", price=10, quantity=200
    )
    product.sync_save()

    # Use atomic update with condition on aliased field
    product.sync_update(
        atomic=[Product.quantity.set(199)],
        condition=Product.quantity > 0,
    )

    loaded = Product.sync_get(pk=f"ALIAS_COND#{uid}", sk="PRODUCT#1")
    assert loaded is not None
    assert loaded.quantity == 199


def test_sync_key_alias_save_and_get(table):
    """Keys with aliases work for save and get."""
    uid = str(uuid.uuid4())[:8]
    thing = Thing(partition=f"KALIAS#{uid}", sort="THING#1", data="hello")
    thing.sync_save()

    loaded = Thing.sync_get(partition=f"KALIAS#{uid}", sort="THING#1")
    assert loaded is not None
    assert loaded.data == "hello"


def test_sync_key_alias_stored_correctly(table):
    """Key aliases are stored as short names in DynamoDB."""
    uid = str(uuid.uuid4())[:8]
    thing = Thing(partition=f"KALIAS_RAW#{uid}", sort="THING#1", data="world")
    thing.sync_save()

    # Read raw - keys should use alias names (pk/sk match the table schema)
    raw = table.sync_get_item("test_table", {"pk": f"KALIAS_RAW#{uid}", "sk": "THING#1"})
    assert raw is not None
    assert raw["pk"] == f"KALIAS_RAW#{uid}"
    assert raw["sk"] == "THING#1"
    assert raw["d"] == "world"


def test_sync_query_with_alias(table):
    """Query works with aliased partition key."""
    uid = str(uuid.uuid4())[:8]
    pk = f"ALIAS_Q#{uid}"
    for i in range(3):
        Product(
            pk=pk, sk=f"PRODUCT#{i}", product_name=f"Item {i}", price=10 * i, quantity=i
        ).sync_save()

    results = list(Product.sync_query(partition_key=pk))
    assert len(results) == 3
    names = {r.product_name for r in results}
    assert names == {"Item 0", "Item 1", "Item 2"}


def test_sync_scan_with_alias(table):
    """Scan returns items with aliases translated back."""
    uid = str(uuid.uuid4())[:8]
    pk = f"ALIAS_SCAN#{uid}"
    Product(pk=pk, sk="ONLY", product_name="Scanner", price=150, quantity=3).sync_save()

    results = list(Product.sync_scan(filter_condition=Product.pk == pk))
    assert len(results) == 1
    assert results[0].product_name == "Scanner"
    assert results[0].price == 150
