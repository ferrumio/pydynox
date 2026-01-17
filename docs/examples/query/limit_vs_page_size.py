from pydynox import Model, ModelConfig
from pydynox.attributes import NumberAttribute, StringAttribute


class Order(Model):
    model_config = ModelConfig(table="orders")
    pk = StringAttribute(hash_key=True)
    sk = StringAttribute(range_key=True)
    total = NumberAttribute()
    status = StringAttribute()


# limit = total items to return (stops after N items)
# page_size = items per DynamoDB request (controls pagination)

# Example 1: Get exactly 10 items total
# DynamoDB will fetch 10 items per request, stop after 10 total
orders = list(Order.query(hash_key="CUSTOMER#123", limit=10))
print(f"Got {len(orders)} orders")  # Always 10 (or less if table has fewer)


# Example 2: Get all items, but fetch 25 per page
# DynamoDB will fetch 25 items per request, return all items
for order in Order.query(hash_key="CUSTOMER#123", page_size=25):
    print(f"Order: {order.sk}")


# Example 3: Get 100 items total, fetching 25 per page
# DynamoDB will make 4 requests (25 + 25 + 25 + 25 = 100)
orders = list(
    Order.query(
        hash_key="CUSTOMER#123",
        limit=100,
        page_size=25,
    )
)
print(f"Got {len(orders)} orders")  # 100 items


# Example 4: Manual pagination with page_size
# Useful for "load more" buttons in UI
result = Order.query(hash_key="CUSTOMER#123", limit=10, page_size=10)
first_page = list(result)
print(f"First page: {len(first_page)} items")

if result.last_evaluated_key:
    # Fetch next page
    result = Order.query(
        hash_key="CUSTOMER#123",
        limit=10,
        page_size=10,
        last_evaluated_key=result.last_evaluated_key,
    )
    second_page = list(result)
    print(f"Second page: {len(second_page)} items")
