"""Reset metrics per request - important for long-running processes."""

import asyncio

from pydynox import Model, ModelConfig
from pydynox.attributes import StringAttribute


class Order(Model):
    model_config = ModelConfig(table="orders")
    pk = StringAttribute(hash_key=True)
    sk = StringAttribute(range_key=True)
    status = StringAttribute()


async def handle_request(order_id: str):
    """Handle a single request - reset metrics at start."""
    # Reset at start of each request
    Order.reset_metrics()

    # Do operations
    order = await Order.get(pk=f"ORDER#{order_id}", sk="DETAILS")
    if order:
        order.status = "processed"
        await order.save()

    # Log metrics for this request only
    total = Order.get_total_metrics()
    print(f"Request metrics: {total.total_rcu} RCU, {total.total_wcu} WCU")


# In FastAPI/Flask, call reset_metrics() at start of each request
# Otherwise metrics accumulate forever

asyncio.run(handle_request("123"))
