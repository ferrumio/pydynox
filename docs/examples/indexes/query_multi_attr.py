# ruff: noqa: F821
# All partition key attributes are required
products = Product.location_index.query(
    tenant_id="ACME",
    region="us-east-1",
)

for product in products:
    print(f"{product.name}: ${product.price}")

# Query category index
phones = Product.category_index.query(
    category="electronics",
    subcategory="phones",
)

# With filter
expensive = Product.location_index.query(
    tenant_id="ACME",
    region="us-east-1",
    filter_condition=Product.price >= 1000,
)
