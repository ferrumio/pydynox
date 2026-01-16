"""Query LSI - find orders by customer with different sort keys."""

from pydynox import Model, ModelConfig, get_default_client
from pydynox.attributes import NumberAttribute, StringAttribute
from pydynox.indexes import LocalSecondaryIndex

client = get_default_client()


class Order(Model):
    """Order model with LSI."""

    model_config = ModelConfig(table="orders_lsi")

    customer_id = StringAttribute(hash_key=True)
    order_id = StringAttribute(range_key=True)
    status = StringAttribute()
    total = NumberAttribute()
    created_at = StringAttribute()

    # LSI for querying by status
    status_index = LocalSecondaryIndex(
        index_name="status-index",
        range_key="status",
    )


# Create table with LSI
if not client.table_exists("orders_lsi"):
    client.create_table(
        "orders_lsi",
        hash_key=("customer_id", "S"),
        range_key=("order_id", "S"),
        local_secondary_indexes=[
            {
                "index_name": "status-index",
                "range_key": ("status", "S"),
                "projection": "ALL",
            }
        ],
    )

# Create some orders
Order(
    customer_id="CUST#1",
    order_id="ORD#001",
    status="pending",
    total=100,
    created_at="2024-01-01",
).save()
Order(
    customer_id="CUST#1",
    order_id="ORD#002",
    status="shipped",
    total=250,
    created_at="2024-01-02",
).save()
Order(
    customer_id="CUST#1",
    order_id="ORD#003",
    status="pending",
    total=75,
    created_at="2024-01-03",
).save()

# Query all orders for customer (using main table)
print("All orders for CUST#1:")
for order in Order.query(hash_key="CUST#1"):
    print(f"  {order.order_id}: {order.status} - ${order.total}")

# Query orders by status using LSI
print("\nPending orders for CUST#1 (via LSI):")
for order in Order.status_index.query(
    customer_id="CUST#1", range_key_condition=Order.status == "pending"
):
    print(f"  {order.order_id}: ${order.total}")
