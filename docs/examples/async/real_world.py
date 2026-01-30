"""Real world async example (async is default - no prefix needed)."""

import asyncio

from pydynox import DynamoDBClient, Model, ModelConfig
from pydynox.attributes import StringAttribute

client = DynamoDBClient()


class User(Model):
    model_config = ModelConfig(table="users")
    pk = StringAttribute(partition_key=True)
    sk = StringAttribute(sort_key=True)
    name = StringAttribute()


async def get_user_with_orders(user_id: str):
    """Fetch user and their orders at the same time."""
    user, orders = await asyncio.gather(
        User.get(pk=f"USER#{user_id}", sk="PROFILE"),
        client.query(
            "orders",
            key_condition_expression="#pk = :pk",
            expression_attribute_names={"#pk": "pk"},
            expression_attribute_values={":pk": f"USER#{user_id}"},
        ).all(),
    )
    return {"user": user, "orders": orders}
