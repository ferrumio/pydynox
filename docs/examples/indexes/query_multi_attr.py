# ruff: noqa: F821
# All partition key attributes are required
async for product in Product.location_index.query(
    tenant_id="ACME",
    region="us-east-1",
):
    print(f"{product.name}: ${product.price}")

# Query category index
async for phone in Product.category_index.query(
    category="electronics",
    subcategory="phones",
):
    print(phone.name)

# With filter
async for product in Product.location_index.query(
    tenant_id="ACME",
    region="us-east-1",
    filter_condition=Product.price >= 1000,
):
    print(f"Expensive: {product.name}")
