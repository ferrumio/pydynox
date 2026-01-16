"""pydynox: Query items from DynamoDB."""

from pydynox import Model, ModelConfig
from pydynox.attributes import NumberAttribute, StringAttribute


class Order(Model):
    model_config = ModelConfig(table="orders")
    pk = StringAttribute(hash_key=True)
    sk = StringAttribute(range_key=True)
    amount = NumberAttribute()


orders = Order.query(
    hash_key="CUSTOMER#123",
    range_key_condition=Order.sk.begins_with("ORDER#"),
    filter_condition=Order.amount > 100,
)

for order in orders:
    print(f"Order: {order.sk}, Amount: {order.amount}")
