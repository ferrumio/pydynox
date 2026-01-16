"""LSI pagination - limit vs page_size behavior."""

from pydynox import Model, ModelConfig, get_default_client
from pydynox.attributes import NumberAttribute, StringAttribute
from pydynox.indexes import LocalSecondaryIndex

client = get_default_client()


class Order(Model):
    """Order model with LSI on created_at."""

    model_config = ModelConfig(table="orders_lsi_pagination")

    pk = StringAttribute(hash_key=True)  # customer_id
    sk = StringAttribute(range_key=True)  # order_id
    created_at = StringAttribute()
    total = NumberAttribute()
    status = StringAttribute()

    created_at_index = LocalSecondaryIndex(
        index_name="created_at-index",
        range_key="created_at",
    )


# Create table with LSI
if not client.table_exists("orders_lsi_pagination"):
    client.create_table(
        "orders_lsi_pagination",
        hash_key=("pk", "S"),
        range_key=("sk", "S"),
        local_secondary_indexes=[
            {
                "index_name": "created_at-index",
                "range_key": ("created_at", "S"),
                "projection": "ALL",
            }
        ],
    )

# Create 25 orders for one customer
for i in range(25):
    Order(
        pk="CUSTOMER#1",
        sk=f"ORDER#{i:03d}",
        created_at=f"2024-01-{i + 1:02d}",
        total=100 + i * 10,
        status="pending" if i % 2 == 0 else "shipped",
    ).save()


# limit = total items to return (stops after N items)
# page_size = items per DynamoDB request (controls pagination)

# Example 1: Get exactly 10 orders for a customer
orders = list(
    Order.created_at_index.query(
        pk="CUSTOMER#1",
        limit=10,
    )
)
print(f"limit=10: Got {len(orders)} orders")


# Example 2: Get all orders, fetching 5 per page
count = 0
for order in Order.created_at_index.query(
    pk="CUSTOMER#1",
    page_size=5,
):
    count += 1
print(f"page_size=5 (no limit): Got {count} orders")


# Example 3: Get 15 orders, fetching 5 per page (3 requests)
orders = list(
    Order.created_at_index.query(
        pk="CUSTOMER#1",
        limit=15,
        page_size=5,
    )
)
print(f"limit=15, page_size=5: Got {len(orders)} orders")


# Example 4: Manual pagination with consistent reads (LSI supports this!)
result = Order.created_at_index.query(
    pk="CUSTOMER#1",
    limit=10,
    page_size=10,
    consistent_read=True,
)
first_page = list(result)
print(f"First page (consistent): {len(first_page)} items")

if result.last_evaluated_key:
    result = Order.created_at_index.query(
        pk="CUSTOMER#1",
        limit=10,
        page_size=10,
        consistent_read=True,
        last_evaluated_key=result.last_evaluated_key,
    )
    second_page = list(result)
    print(f"Second page (consistent): {len(second_page)} items")
