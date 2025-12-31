"""Safe delete - only delete if conditions are met."""

from pydynox import Model, ModelConfig
from pydynox.attributes import NumberAttribute, StringAttribute


class Order(Model):
    model_config = ModelConfig(table="orders")

    pk = StringAttribute(hash_key=True)
    status = StringAttribute()
    total = NumberAttribute()


# Only delete if order is in "draft" status
order = Order.get(pk="ORDER#123")
order.delete(condition=Order.status == "draft")

# Can't delete orders that are already processed
