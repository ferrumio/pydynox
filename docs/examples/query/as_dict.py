"""Query returning dicts instead of Model instances."""

from pydynox import Model, ModelConfig
from pydynox.attributes import NumberAttribute, StringAttribute


class Order(Model):
    model_config = ModelConfig(table="orders")
    pk = StringAttribute(hash_key=True)
    sk = StringAttribute(range_key=True)
    total = NumberAttribute()
    status = StringAttribute()


# Return dicts instead of Model instances
for order in Order.query(hash_key="CUSTOMER#123", as_dict=True):
    # order is a plain dict, not an Order instance
    print(order.get("sk"), order.get("total"))

# Useful for read-only operations where you don't need Model methods
orders = list(Order.query(hash_key="CUSTOMER#123", as_dict=True))
print(f"Found {len(orders)} orders as dicts")
