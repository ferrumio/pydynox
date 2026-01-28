"""Strands CRUD tools example."""

from pydynox import Model, ModelConfig
from pydynox.attributes import NumberAttribute, StringAttribute
from strands import tool


class Customer(Model):
    model_config = ModelConfig(table="customers")

    pk = StringAttribute(hash_key=True)
    sk = StringAttribute(range_key=True)
    name = StringAttribute()
    email = StringAttribute()


class Order(Model):
    model_config = ModelConfig(table="orders")

    pk = StringAttribute(hash_key=True)
    sk = StringAttribute(range_key=True)
    order_id = StringAttribute()
    status = StringAttribute()
    total = NumberAttribute()


@tool
def create_customer(customer_id: str, name: str, email: str) -> dict:
    """Create a new customer."""
    customer = Customer(
        pk=f"CUSTOMER#{customer_id}",
        sk="PROFILE",
        name=name,
        email=email,
    )
    customer.sync_save()
    return {"success": True, "customer_id": customer_id}


@tool
def update_customer(customer_id: str, name: str = None, email: str = None) -> dict:
    """Update customer details."""
    customer = Customer.sync_get(pk=f"CUSTOMER#{customer_id}", sk="PROFILE")
    if not customer:
        return {"error": "Customer not found"}

    updates = {}
    if name:
        updates["name"] = name
    if email:
        updates["email"] = email

    if updates:
        customer.sync_update(**updates)

    return {"success": True}


@tool
def delete_customer(customer_id: str) -> dict:
    """Delete a customer."""
    customer = Customer.sync_get(pk=f"CUSTOMER#{customer_id}", sk="PROFILE")
    if not customer:
        return {"error": "Customer not found"}

    customer.sync_delete()
    return {"success": True}


@tool
def search_orders(customer_id: str, status: str = None, limit: int = 10) -> list:
    """Search orders for a customer.

    Args:
        customer_id: The customer ID.
        status: Filter by status (optional).
        limit: Max results to return.
    """
    query_params = {
        "key_condition": "pk = :pk AND begins_with(sk, :prefix)",
        "expression_values": {
            ":pk": f"CUSTOMER#{customer_id}",
            ":prefix": "ORDER#",
        },
        "limit": limit,
    }

    if status:
        query_params["filter_condition"] = "status = :status"
        query_params["expression_values"][":status"] = status

    orders = list(Order.sync_query(**query_params))
    return [{"order_id": o.order_id, "status": o.status} for o in orders]


@tool
def get_order_status(order_id: str) -> dict:
    """Get the current status of an order.

    Use this when a customer asks about their order status,
    shipping updates, or delivery estimates.

    Args:
        order_id: The order ID (e.g., "ORD-12345").

    Returns:
        Order status including: status, tracking number, estimated delivery.
    """
    orders = list(
        Order.sync_scan(
            filter_condition="order_id = :order_id",
            expression_values={":order_id": order_id},
            limit=1,
        )
    )

    if not orders:
        return {"error": "Order not found"}

    order = orders[0]
    return {"order_id": order.order_id, "status": order.status, "total": order.total}
