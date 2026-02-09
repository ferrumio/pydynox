"""Create table with LSI using Model.create_table()."""

import asyncio

from pydynox import DynamoDBClient, Model, ModelConfig, set_default_client
from pydynox.attributes import NumberAttribute, StringAttribute
from pydynox.indexes import LocalSecondaryIndex

# Setup client
client = DynamoDBClient()
set_default_client(client)


class Order(Model):
    """Order model with LSI - table created automatically from model definition."""

    model_config = ModelConfig(table="orders_model_lsi")

    customer_id = StringAttribute(partition_key=True)
    order_id = StringAttribute(sort_key=True)
    status = StringAttribute()
    total = NumberAttribute()

    # LSI defined on model
    status_index = LocalSecondaryIndex(
        index_name="status-index",
        sort_key="status",
    )


async def main():
    # Create table from model definition
    # LSIs are automatically included!
    if not await Order.table_exists():
        await Order.create_table(wait=True)
        print("Table created with LSI")

    # Use the model
    await Order(
        customer_id="CUST#1",
        order_id="ORD#001",
        status="pending",
        total=100,
    ).save()

    # Query using LSI
    async for order in Order.status_index.query(partition_key="CUST#1"):
        print(f"Order: {order.order_id} - {order.status}")


asyncio.run(main())


asyncio.run(main())
