from pydynox import Model, ModelConfig
from pydynox.attributes import NumberAttribute, StringAttribute


class Order(Model):
    model_config = ModelConfig(table="orders")
    pk = StringAttribute(hash_key=True)
    sk = StringAttribute(range_key=True)
    total = NumberAttribute()
    status = StringAttribute()


# Ascending order (default)
for order in Order.query(
    hash_key="CUSTOMER#123",
    scan_index_forward=True,
):
    print(f"Order: {order.sk}")

# Descending order
for order in Order.query(
    hash_key="CUSTOMER#123",
    scan_index_forward=False,
):
    print(f"Order: {order.sk}")

# Get the 5 most recent orders (descending)
recent_orders = list(
    Order.query(
        hash_key="CUSTOMER#123",
        scan_index_forward=False,
        limit=5,
    )
)

for order in recent_orders:
    print(f"Recent order: {order.sk}")
