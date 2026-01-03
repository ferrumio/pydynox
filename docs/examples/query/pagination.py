from pydynox import Model, ModelConfig
from pydynox.attributes import NumberAttribute, StringAttribute


class Order(Model):
    model_config = ModelConfig(table="orders")
    pk = StringAttribute(hash_key=True)
    sk = StringAttribute(range_key=True)
    total = NumberAttribute()
    status = StringAttribute()


# Automatic pagination - iterator fetches all pages
for order in Order.query(hash_key="CUSTOMER#123"):
    print(f"Order: {order.sk}")

# Manual pagination - control page size
result = Order.query(hash_key="CUSTOMER#123", limit=10)

# Process first page
page_count = 0
for order in result:
    print(f"Order: {order.sk}")
    page_count += 1
    if page_count >= 10:
        break

# Check if there are more pages
if result.last_evaluated_key:
    print("More pages available")

    # Fetch next page
    next_result = Order.query(
        hash_key="CUSTOMER#123",
        limit=10,
        last_evaluated_key=result.last_evaluated_key,
    )
    for order in next_result:
        print(f"Next page order: {order.sk}")
