"""Basic query examples (sync - use sync_ prefix)."""

from pydynox import Model, ModelConfig, get_default_client
from pydynox.attributes import NumberAttribute, StringAttribute

client = get_default_client()


class Order(Model):
    model_config = ModelConfig(table="orders")
    pk = StringAttribute(partition_key=True)
    sk = StringAttribute(sort_key=True)
    total = NumberAttribute()
    status = StringAttribute()


def main():
    # Setup: create table and data
    if not client.sync_table_exists("orders"):
        client.sync_create_table(
            "orders",
            partition_key=("pk", "S"),
            sort_key=("sk", "S"),
        )

    # Create some orders
    for i in range(3):
        Order(
            pk="CUSTOMER#123",
            sk=f"ORDER#{i:03d}",
            total=100 + i * 50,
            status="pending",
        ).sync_save()

    # Query all orders for a customer
    for order in Order.sync_query(partition_key="CUSTOMER#123"):
        print(f"Order: {order.sk}, Total: {order.total}")

    # Get first result only
    first_order = Order.sync_query(partition_key="CUSTOMER#123").first()
    if first_order:
        print(f"First order: {first_order.sk}")

    # Collect all results into a list
    orders = list(Order.sync_query(partition_key="CUSTOMER#123"))
    print(f"Found {len(orders)} orders")


main()
