"""Async integration tests for field alias feature.

Tests that aliases work end-to-end with real DynamoDB (LocalStack).
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


@pytest.mark.asyncio
async def test_save_and_get_with_alias(table):
    """Save with Python names, get back with Python names."""
    uid = str(uuid.uuid4())[:8]
    product = Product(
        pk=f"AALIAS#{uid}", sk="PRODUCT#1", product_name="Laptop", price=999, quantity=5
    )
    await product.save()

    loaded = await Product.get(pk=f"AALIAS#{uid}", sk="PRODUCT#1")
    assert loaded is not None
    assert loaded.product_name == "Laptop"
    assert loaded.price == 999
    assert loaded.quantity == 5


@pytest.mark.asyncio
async def test_alias_stored_as_short_names(table):
    """Verify DynamoDB stores the alias names, not Python names."""
    uid = str(uuid.uuid4())[:8]
    product = Product(
        pk=f"AALIAS_RAW#{uid}", sk="PRODUCT#1", product_name="Mouse", price=25, quantity=100
    )
    await product.save()

    # Read raw item from DynamoDB (bypassing Model)
    raw = await table.get_item("test_table", {"pk": f"AALIAS_RAW#{uid}", "sk": "PRODUCT#1"})
    assert raw is not None
    assert raw["pn"] == "Mouse"
    assert raw["pr"] == 25
    assert raw["q"] == 100
    assert "product_name" not in raw
    assert "price" not in raw
    assert "quantity" not in raw


@pytest.mark.asyncio
async def test_update_with_alias(table):
    """Update aliased fields by Python name."""
    uid = str(uuid.uuid4())[:8]
    product = Product(
        pk=f"AALIAS_UPD#{uid}", sk="PRODUCT#1", product_name="Keyboard", price=75, quantity=50
    )
    await product.save()

    await product.update(price=80)

    loaded = await Product.get(pk=f"AALIAS_UPD#{uid}", sk="PRODUCT#1")
    assert loaded is not None
    assert loaded.price == 80
    assert loaded.product_name == "Keyboard"


@pytest.mark.asyncio
async def test_delete_with_alias(table):
    """Delete item that has aliased fields."""
    uid = str(uuid.uuid4())[:8]
    product = Product(
        pk=f"AALIAS_DEL#{uid}", sk="PRODUCT#1", product_name="Monitor", price=300, quantity=10
    )
    await product.save()

    await product.delete()

    loaded = await Product.get(pk=f"AALIAS_DEL#{uid}", sk="PRODUCT#1")
    assert loaded is None


@pytest.mark.asyncio
async def test_condition_with_alias(table):
    """Conditions use alias names in DynamoDB expressions."""
    uid = str(uuid.uuid4())[:8]
    product = Product(
        pk=f"AALIAS_COND#{uid}", sk="PRODUCT#1", product_name="Cable", price=10, quantity=200
    )
    await product.save()

    # Use atomic update with condition on aliased field
    await product.update(
        atomic=[Product.quantity.set(199)],
        condition=Product.quantity > 0,
    )

    loaded = await Product.get(pk=f"AALIAS_COND#{uid}", sk="PRODUCT#1")
    assert loaded is not None
    assert loaded.quantity == 199


@pytest.mark.asyncio
async def test_key_alias_save_and_get(table):
    """Keys with aliases work for save and get."""
    uid = str(uuid.uuid4())[:8]
    thing = Thing(partition=f"AKALIAS#{uid}", sort="THING#1", data="hello")
    await thing.save()

    loaded = await Thing.get(partition=f"AKALIAS#{uid}", sort="THING#1")
    assert loaded is not None
    assert loaded.data == "hello"


@pytest.mark.asyncio
async def test_key_alias_stored_correctly(table):
    """Key aliases are stored as short names in DynamoDB."""
    uid = str(uuid.uuid4())[:8]
    thing = Thing(partition=f"AKALIAS_RAW#{uid}", sort="THING#1", data="world")
    await thing.save()

    raw = await table.get_item("test_table", {"pk": f"AKALIAS_RAW#{uid}", "sk": "THING#1"})
    assert raw is not None
    assert raw["pk"] == f"AKALIAS_RAW#{uid}"
    assert raw["sk"] == "THING#1"
    assert raw["d"] == "world"


@pytest.mark.asyncio
async def test_query_with_alias(table):
    """Query works with aliased partition key."""
    uid = str(uuid.uuid4())[:8]
    pk = f"AALIAS_Q#{uid}"
    for i in range(3):
        await Product(
            pk=pk, sk=f"PRODUCT#{i}", product_name=f"Item {i}", price=10 * i, quantity=i
        ).save()

    results = [item async for item in Product.query(partition_key=pk)]
    assert len(results) == 3
    names = {r.product_name for r in results}
    assert names == {"Item 0", "Item 1", "Item 2"}


@pytest.mark.asyncio
async def test_atomic_update_with_alias(table):
    """Atomic updates use alias names in expressions."""
    uid = str(uuid.uuid4())[:8]
    product = Product(
        pk=f"AALIAS_ATOM#{uid}", sk="PRODUCT#1", product_name="Widget", price=50, quantity=10
    )
    await product.save()

    await product.update(atomic=[Product.quantity.add(5)])

    loaded = await Product.get(pk=f"AALIAS_ATOM#{uid}", sk="PRODUCT#1")
    assert loaded is not None
    assert loaded.quantity == 15
