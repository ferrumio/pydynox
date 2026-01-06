"""Best practices for agentic tools."""

from pydynox import Model, ModelConfig
from pydynox.attributes import EncryptedAttribute, NumberAttribute, StringAttribute
from strands import tool


class Order(Model):
    model_config = ModelConfig(table="orders")

    pk = StringAttribute(hash_key=True)
    sk = StringAttribute(range_key=True)
    order_id = StringAttribute()
    status = StringAttribute()
    total = NumberAttribute()


class Customer(Model):
    model_config = ModelConfig(table="customers")

    pk = StringAttribute(hash_key=True)
    sk = StringAttribute(range_key=True)
    name = StringAttribute()
    email = StringAttribute()


class Employee(Model):
    model_config = ModelConfig(table="employees")

    pk = StringAttribute(hash_key=True)
    sk = StringAttribute(range_key=True)
    name = StringAttribute()
    department = StringAttribute()
    ssn = EncryptedAttribute(key_id="alias/hr-key")


# Return structured data
@tool
def get_order(order_id: str) -> dict:
    """Get order details."""
    order = Order.get(pk=order_id, sk="DETAILS")

    if not order:
        return {"found": False, "error": "Order not found"}

    return {
        "found": True,
        "order_id": order.order_id,
        "status": order.status,
        "total": order.total,
    }


# Handle errors gracefully
@tool
def delete_customer(customer_id: str) -> dict:
    """Delete a customer."""
    customer = Customer.get(pk=f"CUSTOMER#{customer_id}", sk="PROFILE")

    if not customer:
        return {"success": False, "error": "Not found"}

    customer.delete()
    return {"success": True}


# Write good docstrings
@tool
def search_orders(customer_id: str, status: str = None) -> list:
    """Search orders for a customer.

    Use this when a customer asks about their orders,
    order history, or wants to find a specific order.

    Args:
        customer_id: The customer's unique ID.
        status: Filter by status (shipped, pending, delivered).

    Returns:
        List of orders with order_id, status, and total.
    """
    query_params = {
        "key_condition": "pk = :pk",
        "expression_values": {":pk": f"CUSTOMER#{customer_id}"},
    }

    if status:
        query_params["filter_condition"] = "status = :status"
        query_params["expression_values"][":status"] = status

    orders = Order.query(**query_params)
    return [{"order_id": o.order_id, "status": o.status, "total": o.total} for o in orders]


# Bad - exposes sensitive data
@tool
def get_employee_bad(employee_id: str) -> dict:
    """Get employee (BAD - exposes SSN)."""
    emp = Employee.get(pk=f"EMP#{employee_id}", sk="PROFILE")
    if not emp:
        return {"error": "Not found"}
    return {"name": emp.name, "ssn": emp.ssn}  # Don't expose SSN!


# Good - protects sensitive data
@tool
def get_employee_good(employee_id: str) -> dict:
    """Get employee (GOOD - no sensitive data)."""
    emp = Employee.get(pk=f"EMP#{employee_id}", sk="PROFILE")
    if not emp:
        return {"error": "Not found"}
    return {"name": emp.name, "department": emp.department}
