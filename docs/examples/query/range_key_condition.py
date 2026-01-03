from pydynox import Model, ModelConfig
from pydynox.attributes import NumberAttribute, StringAttribute


class Order(Model):
    model_config = ModelConfig(table="orders")
    pk = StringAttribute(hash_key=True)
    sk = StringAttribute(range_key=True)
    total = NumberAttribute()
    status = StringAttribute()


# Query orders that start with "ORDER#"
for order in Order.query(
    hash_key="CUSTOMER#123",
    range_key_condition=Order.sk.begins_with("ORDER#"),
):
    print(f"Order: {order.sk}")

# Query orders between two sort keys
for order in Order.query(
    hash_key="CUSTOMER#123",
    range_key_condition=Order.sk.between("ORDER#001", "ORDER#010"),
):
    print(f"Order: {order.sk}")

# Query orders greater than a sort key
for order in Order.query(
    hash_key="CUSTOMER#123",
    range_key_condition=Order.sk > "ORDER#005",
):
    print(f"Order: {order.sk}")
