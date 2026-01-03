from pydynox import Model, ModelConfig
from pydynox.attributes import NumberAttribute, StringAttribute


class Order(Model):
    model_config = ModelConfig(table="orders")
    pk = StringAttribute(hash_key=True)
    sk = StringAttribute(range_key=True)
    total = NumberAttribute()
    status = StringAttribute()


# Filter by status
for order in Order.query(
    hash_key="CUSTOMER#123",
    filter_condition=Order.status == "shipped",
):
    print(f"Shipped order: {order.sk}")

# Filter by total amount
for order in Order.query(
    hash_key="CUSTOMER#123",
    filter_condition=Order.total >= 100,
):
    print(f"Large order: {order.sk}, Total: {order.total}")

# Combine multiple filters with & (AND)
for order in Order.query(
    hash_key="CUSTOMER#123",
    filter_condition=(Order.status == "shipped") & (Order.total > 50),
):
    print(f"Shipped large order: {order.sk}")

# Combine filters with | (OR)
for order in Order.query(
    hash_key="CUSTOMER#123",
    filter_condition=(Order.status == "shipped") | (Order.status == "delivered"),
):
    print(f"Completed order: {order.sk}")
