"""Integration tests for multi-attribute GSI keys.

Tests the new DynamoDB feature (Nov 2025) that allows up to 4 attributes
per partition key and 4 per sort key in GSIs.

NOTE: LocalStack does not support multi-attribute GSI keys yet.
These tests require real DynamoDB or a compatible emulator.
Mark with @pytest.mark.skip_localstack to skip in CI.
"""

import pytest
from pydynox import DynamoDBClient, Model, ModelConfig, set_default_client
from pydynox.attributes import NumberAttribute, StringAttribute
from pydynox.indexes import GlobalSecondaryIndex

# Skip all tests in this module - LocalStack doesn't support multi-attribute GSI
pytestmark = pytest.mark.skip(
    reason="LocalStack does not support multi-attribute GSI keys (Nov 2025 feature)"
)


@pytest.fixture
def multi_attr_client(dynamodb_endpoint):
    """Create a client and table with multi-attribute GSIs."""
    client = DynamoDBClient(
        region="us-east-1",
        endpoint_url=dynamodb_endpoint,
        access_key="testing",
        secret_key="testing",
    )

    table_name = "multi_attr_gsi_test"

    # Delete if exists
    if client.sync_table_exists(table_name):
        client.sync_delete_table(table_name)

    # Create table with multi-attribute GSI
    client.sync_create_table(
        table_name,
        partition_key=("pk", "S"),
        sort_key=("sk", "S"),
        global_secondary_indexes=[
            {
                "index_name": "location-index",
                "partition_keys": [("tenant_id", "S"), ("region", "S")],
                "sort_keys": [("created_at", "S"), ("item_id", "S")],
                "projection": "ALL",
            },
            {
                "index_name": "category-index",
                "partition_keys": [("category", "S"), ("subcategory", "S")],
                "projection": "ALL",
            },
        ],
    )

    set_default_client(client)
    return client


class Product(Model):
    """Test model with multi-attribute GSIs."""

    model_config = ModelConfig(table="multi_attr_gsi_test")

    pk = StringAttribute(partition_key=True)
    sk = StringAttribute(sort_key=True)
    tenant_id = StringAttribute()
    region = StringAttribute()
    created_at = StringAttribute()
    item_id = StringAttribute()
    category = StringAttribute()
    subcategory = StringAttribute()
    name = StringAttribute()
    price = NumberAttribute()

    # Multi-attribute GSI with 2 hash keys and 2 range keys
    location_index = GlobalSecondaryIndex(
        index_name="location-index",
        partition_key=["tenant_id", "region"],
        sort_key=["created_at", "item_id"],
    )

    # Multi-attribute GSI with 2 hash keys only
    category_index = GlobalSecondaryIndex(
        index_name="category-index",
        partition_key=["category", "subcategory"],
    )


@pytest.mark.asyncio
async def test_multi_attr_gsi_query_basic(multi_attr_client):
    """Test basic query on multi-attribute GSI."""
    # GIVEN products in different regions
    p1 = Product(
        pk="PROD#1",
        sk="DATA",
        tenant_id="ACME",
        region="us-east-1",
        created_at="2025-01-01",
        item_id="001",
        category="electronics",
        subcategory="phones",
        name="iPhone",
        price=999,
    )
    await p1.save()

    p2 = Product(
        pk="PROD#2",
        sk="DATA",
        tenant_id="ACME",
        region="us-east-1",
        created_at="2025-01-02",
        item_id="002",
        category="electronics",
        subcategory="laptops",
        name="MacBook",
        price=1999,
    )
    await p2.save()

    p3 = Product(
        pk="PROD#3",
        sk="DATA",
        tenant_id="ACME",
        region="eu-west-1",
        created_at="2025-01-01",
        item_id="003",
        category="electronics",
        subcategory="phones",
        name="Galaxy",
        price=899,
    )
    await p3.save()

    # WHEN querying by tenant_id + region (both hash key attrs required)
    results = [
        x
        async for x in Product.location_index.query(
            tenant_id="ACME",
            region="us-east-1",
        )
    ]

    # THEN only us-east-1 products should be returned
    assert len(results) == 2
    names = {r.name for r in results}
    assert names == {"iPhone", "MacBook"}


@pytest.mark.asyncio
async def test_multi_attr_gsi_query_different_tenant(multi_attr_client):
    """Test query returns only matching tenant/region combo."""
    # GIVEN products for different tenants
    p1 = Product(
        pk="PROD#10",
        sk="DATA",
        tenant_id="ACME",
        region="us-east-1",
        created_at="2025-01-01",
        item_id="010",
        category="books",
        subcategory="fiction",
        name="Book A",
        price=20,
    )
    await p1.save()

    p2 = Product(
        pk="PROD#11",
        sk="DATA",
        tenant_id="GLOBEX",
        region="us-east-1",
        created_at="2025-01-01",
        item_id="011",
        category="books",
        subcategory="fiction",
        name="Book B",
        price=25,
    )
    await p2.save()

    # WHEN querying ACME only
    results = [
        x
        async for x in Product.location_index.query(
            tenant_id="ACME",
            region="us-east-1",
        )
    ]

    # THEN only ACME products should be returned
    assert len(results) == 1
    assert results[0].name == "Book A"
    assert results[0].tenant_id == "ACME"


@pytest.mark.asyncio
async def test_multi_attr_gsi_query_category_index(multi_attr_client):
    """Test query on category index (2 hash keys, no range key)."""
    # GIVEN products in different subcategories
    p1 = Product(
        pk="PROD#20",
        sk="DATA",
        tenant_id="ACME",
        region="us-east-1",
        created_at="2025-01-01",
        item_id="020",
        category="clothing",
        subcategory="shirts",
        name="T-Shirt",
        price=30,
    )
    await p1.save()

    p2 = Product(
        pk="PROD#21",
        sk="DATA",
        tenant_id="ACME",
        region="us-east-1",
        created_at="2025-01-02",
        item_id="021",
        category="clothing",
        subcategory="shirts",
        name="Polo",
        price=50,
    )
    await p2.save()

    p3 = Product(
        pk="PROD#22",
        sk="DATA",
        tenant_id="ACME",
        region="us-east-1",
        created_at="2025-01-01",
        item_id="022",
        category="clothing",
        subcategory="pants",
        name="Jeans",
        price=80,
    )
    await p3.save()

    # WHEN querying clothing/shirts
    results = [
        x
        async for x in Product.category_index.query(
            category="clothing",
            subcategory="shirts",
        )
    ]

    # THEN only shirts should be returned
    assert len(results) == 2
    names = {r.name for r in results}
    assert names == {"T-Shirt", "Polo"}


@pytest.mark.asyncio
async def test_multi_attr_gsi_query_with_filter(multi_attr_client):
    """Test multi-attribute GSI query with filter condition."""
    # GIVEN products with different prices
    p1 = Product(
        pk="PROD#30",
        sk="DATA",
        tenant_id="FILTER_TEST",
        region="us-west-2",
        created_at="2025-01-01",
        item_id="030",
        category="toys",
        subcategory="games",
        name="Cheap Game",
        price=10,
    )
    await p1.save()

    p2 = Product(
        pk="PROD#31",
        sk="DATA",
        tenant_id="FILTER_TEST",
        region="us-west-2",
        created_at="2025-01-02",
        item_id="031",
        category="toys",
        subcategory="games",
        name="Expensive Game",
        price=100,
    )
    await p2.save()

    # WHEN querying with price filter
    results = [
        x
        async for x in Product.location_index.query(
            tenant_id="FILTER_TEST",
            region="us-west-2",
            filter_condition=Product.price >= 50,
        )
    ]

    # THEN only expensive items should be returned
    assert len(results) == 1
    assert results[0].name == "Expensive Game"


@pytest.mark.asyncio
async def test_multi_attr_gsi_query_empty_result(multi_attr_client):
    """Test multi-attribute GSI query with no matches."""
    # WHEN querying for non-existent tenant/region
    results = [
        x
        async for x in Product.location_index.query(
            tenant_id="NONEXISTENT",
            region="nowhere",
        )
    ]

    # THEN no results should be returned
    assert len(results) == 0


@pytest.mark.asyncio
async def test_multi_attr_gsi_query_returns_model_instances(multi_attr_client):
    """Test that query returns proper model instances."""
    # GIVEN a product in the table
    p = Product(
        pk="PROD#40",
        sk="DATA",
        tenant_id="INSTANCE_TEST",
        region="ap-south-1",
        created_at="2025-01-01",
        item_id="040",
        category="food",
        subcategory="snacks",
        name="Chips",
        price=5,
    )
    await p.save()

    # WHEN querying via GSI
    results = [
        x
        async for x in Product.location_index.query(
            tenant_id="INSTANCE_TEST",
            region="ap-south-1",
        )
    ]

    # THEN result should be a Product instance with all attributes
    assert len(results) == 1
    product = results[0]

    assert isinstance(product, Product)
    assert product.pk == "PROD#40"
    assert product.tenant_id == "INSTANCE_TEST"
    assert product.region == "ap-south-1"
    assert product.name == "Chips"
    assert product.price == 5


@pytest.mark.asyncio
async def test_multi_attr_gsi_query_requires_all_partition_keys(multi_attr_client):
    """Test that query fails if not all hash keys provided."""
    # WHEN querying with missing hash key
    # THEN ValueError should be raised
    with pytest.raises(ValueError, match="requires 'region'"):
        [x async for x in Product.location_index.query(tenant_id="ACME")]

    with pytest.raises(ValueError, match="requires 'subcategory'"):
        [x async for x in Product.category_index.query(category="electronics")]
