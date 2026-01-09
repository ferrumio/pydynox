"""Safe delete - only delete if conditions are met."""

from pydynox import Model, ModelConfig
from pydynox.attributes import NumberAttribute, StringAttribute


class Order(Model):
    model_config = ModelConfig(table="orders")

    pk = StringAttribute(hash_key=True)
    sk = StringAttribute(range_key=True)
    status = StringAttribute()
    total = NumberAttribute()


# Create an order first
order = Order(pk="ORDER#123", sk="DETAILS", status="draft", total=100)
order.save()

# Only delete if order is in "draft" status
order.delete(condition=Order.status == "draft")

# Can't delete orders that are already processed
