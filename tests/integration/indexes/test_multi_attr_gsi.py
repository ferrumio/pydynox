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
    if client.table_exists(table_name):
        client.delete_table(table_name)

    # Create table with multi-attribute GSI
    client.create_table(
        table_name,
        hash_key=("pk", "S"),
        range_key=("sk", "S"),
        global_secondary_indexes=[
            {
                "index_name": "location-index",
                "hash_keys": [("tenant_id", "S"), ("region", "S")],
                "range_keys": [("created_at", "S"), ("item_id", "S")],
                "projection": "ALL",
            },
            {
                "index_name": "category-index",
                "hash_keys": [("category", "S"), ("subcategory", "S")],
                "projection": "ALL",
            },
        ],
    )

    set_default_client(client)
    return client


class Product(Model):
    """Test model with multi-attribute GSIs."""

    model_config = ModelConfig(table="multi_attr_gsi_test")

    pk = StringAttribute(hash_key=True)
    sk = StringAttribute(range_key=True)
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
        hash_key=["tenant_id", "region"],
        range_key=["created_at", "item_id"],
    )

    # Multi-attribute GSI with 2 hash keys only
    category_index = GlobalSecondaryIndex(
        index_name="category-index",
        hash_key=["category", "subcategory"],
    )


def test_multi_attr_gsi_query_basic(multi_attr_client):
    """Test basic query on multi-attribute GSI."""
    # Create test products
    Product(
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
    ).save()

    Product(
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
    ).save()

    Product(
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
    ).save()

    # Query by tenant_id + region (both hash key attrs required)
    results = list(
        Product.location_index.query(
            tenant_id="ACME",
            region="us-east-1",
        )
    )

    assert len(results) == 2
    names = {r.name for r in results}
    assert names == {"iPhone", "MacBook"}


def test_multi_attr_gsi_query_different_tenant(multi_attr_client):
    """Test query returns only matching tenant/region combo."""
    # Create products for different tenants
    Product(
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
    ).save()

    Product(
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
    ).save()

    # Query ACME only
    results = list(
        Product.location_index.query(
            tenant_id="ACME",
            region="us-east-1",
        )
    )

    assert len(results) == 1
    assert results[0].name == "Book A"
    assert results[0].tenant_id == "ACME"


def test_multi_attr_gsi_query_category_index(multi_attr_client):
    """Test query on category index (2 hash keys, no range key)."""
    Product(
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
    ).save()

    Product(
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
    ).save()

    Product(
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
    ).save()

    # Query clothing/shirts
    results = list(
        Product.category_index.query(
            category="clothing",
            subcategory="shirts",
        )
    )

    assert len(results) == 2
    names = {r.name for r in results}
    assert names == {"T-Shirt", "Polo"}


def test_multi_attr_gsi_query_with_filter(multi_attr_client):
    """Test multi-attribute GSI query with filter condition."""
    Product(
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
    ).save()

    Product(
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
    ).save()

    # Query with price filter
    results = list(
        Product.location_index.query(
            tenant_id="FILTER_TEST",
            region="us-west-2",
            filter_condition=Product.price >= 50,
        )
    )

    assert len(results) == 1
    assert results[0].name == "Expensive Game"


def test_multi_attr_gsi_query_empty_result(multi_attr_client):
    """Test multi-attribute GSI query with no matches."""
    results = list(
        Product.location_index.query(
            tenant_id="NONEXISTENT",
            region="nowhere",
        )
    )

    assert len(results) == 0


def test_multi_attr_gsi_query_returns_model_instances(multi_attr_client):
    """Test that query returns proper model instances."""
    Product(
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
    ).save()

    results = list(
        Product.location_index.query(
            tenant_id="INSTANCE_TEST",
            region="ap-south-1",
        )
    )

    assert len(results) == 1
    product = results[0]

    # Should be a Product instance
    assert isinstance(product, Product)

    # Should have all attributes
    assert product.pk == "PROD#40"
    assert product.tenant_id == "INSTANCE_TEST"
    assert product.region == "ap-south-1"
    assert product.name == "Chips"
    assert product.price == 5


def test_multi_attr_gsi_query_requires_all_hash_keys(multi_attr_client):
    """Test that query fails if not all hash keys provided."""
    with pytest.raises(ValueError, match="Missing"):
        list(Product.location_index.query(tenant_id="ACME"))

    with pytest.raises(ValueError, match="Missing"):
        list(Product.category_index.query(category="electronics"))
