"""Quick example of a pydynox tool for agents."""

from pydynox import Model, ModelConfig
from pydynox.attributes import StringAttribute
from strands import tool


class Customer(Model):
    model_config = ModelConfig(table="customers")

    pk = StringAttribute(hash_key=True)
    sk = StringAttribute(range_key=True)
    email = StringAttribute()
    name = StringAttribute()


@tool
def get_customer(customer_id: str) -> dict:
    """Get customer by ID."""
    customer = Customer.sync_get(pk=f"CUSTOMER#{customer_id}", sk="PROFILE")

    if not customer:
        return {"error": "Not found"}

    return {"name": customer.name, "email": customer.email}
