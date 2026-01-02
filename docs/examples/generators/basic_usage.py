from pydynox import AutoGenerate, Model, ModelConfig
from pydynox.attributes import NumberAttribute, StringAttribute


class Order(Model):
    model_config = ModelConfig(table="orders")

    pk = StringAttribute(hash_key=True, default=AutoGenerate.ULID)
    sk = StringAttribute(range_key=True)
    total = NumberAttribute()


# Create order without providing pk
order = Order(sk="ORDER#DETAILS", total=99.99)
print(order.pk)  # None

order.save()
print(order.pk)  # "01ARZ3NDEKTSV4RRFFQ69G5FAV" (generated ULID)
