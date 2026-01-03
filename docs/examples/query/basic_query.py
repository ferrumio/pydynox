from pydynox import Model, ModelConfig
from pydynox.attributes import NumberAttribute, StringAttribute


class Order(Model):
    model_config = ModelConfig(table="orders")
    pk = StringAttribute(hash_key=True)
    sk = StringAttribute(range_key=True)
    total = NumberAttribute()
    status = StringAttribute()


# Query all orders for a customer
for order in Order.query(hash_key="CUSTOMER#123"):
    print(f"Order: {order.sk}, Total: {order.total}")

# Get first result only
first_order = Order.query(hash_key="CUSTOMER#123").first()
if first_order:
    print(f"First order: {first_order.sk}")

# Collect all results into a list
orders = list(Order.query(hash_key="CUSTOMER#123"))
print(f"Found {len(orders)} orders")
