"""Strands Agents integration with pydynox.

Use case: Customer support agent that can look up customers and orders.
"""

from __future__ import annotations

from pydynox import DynamoDBClient, Model, ModelConfig, set_default_client
from pydynox.attributes import NumberAttribute, StringAttribute
from strands import Agent, tool

# Create client
client = DynamoDBClient(region="us-east-1")
set_default_client(client)


# Define models
class Customer(Model):
    model_config = ModelConfig(table="customers")

    pk = StringAttribute(hash_key=True)  # CUSTOMER#<id>
    sk = StringAttribute(range_key=True)  # PROFILE
    email = StringAttribute()
    name = StringAttribute()


class Order(Model):
    model_config = ModelConfig(table="orders")

    pk = StringAttribute(hash_key=True)  # CUSTOMER#<id>
    sk = StringAttribute(range_key=True)  # ORDER#<timestamp>
    order_id = StringAttribute()
    status = StringAttribute()
    tracking = StringAttribute(default=None)
    total = NumberAttribute()


# Define tools using @tool decorator
@tool
def get_customer_by_email(email: str) -> dict:
    """Look up a customer by their email address.

    Args:
        email: The customer's email address.

    Returns:
        Customer info with id, name, and email. Returns error if not found.
    """
    # Scan with filter since we don't have a GSI in this example
    results = list(Customer.sync_scan(filter_condition=Customer.email == email, limit=1))

    if not results:
        return {"error": f"No customer found with email {email}"}

    customer = results[0]
    return {
        "customer_id": customer.pk.replace("CUSTOMER#", ""),
        "name": customer.name,
        "email": customer.email,
    }


@tool
def get_customer_by_id(customer_id: str) -> dict:
    """Get customer details by their ID.

    Args:
        customer_id: The customer's unique identifier.

    Returns:
        Customer info with name and email. Returns error if not found.
    """
    customer = Customer.sync_get(pk=f"CUSTOMER#{customer_id}", sk="PROFILE")

    if not customer:
        return {"error": f"Customer {customer_id} not found"}

    return {
        "customer_id": customer_id,
        "name": customer.name,
        "email": customer.email,
    }


@tool
def get_recent_orders(customer_id: str, limit: int = 5) -> list:
    """Get a customer's recent orders.

    Args:
        customer_id: The customer's unique identifier.
        limit: Maximum number of orders to return (default 5).

    Returns:
        List of orders with order_id, status, tracking, and total.
    """
    orders = list(
        Order.sync_query(
            hash_key=f"CUSTOMER#{customer_id}",
            range_key_condition=Order.sk.begins_with("ORDER#"),
            scan_index_forward=False,
            limit=limit,
        )
    )

    return [
        {
            "order_id": order.order_id,
            "status": order.status,
            "tracking": order.tracking,
            "total": order.total,
        }
        for order in orders
    ]


@tool
def get_order_status(customer_id: str, order_id: str) -> dict:
    """Get the status of a specific order.

    Args:
        customer_id: The customer's unique identifier.
        order_id: The order's unique identifier.

    Returns:
        Order status and tracking info. Returns error if not found.
    """
    orders = list(
        Order.sync_query(
            hash_key=f"CUSTOMER#{customer_id}",
            range_key_condition=Order.sk.begins_with("ORDER#"),
            filter_condition=Order.order_id == order_id,
            limit=1,
        )
    )

    if not orders:
        return {"error": f"Order {order_id} not found"}

    order = orders[0]
    return {
        "order_id": order.order_id,
        "status": order.status,
        "tracking": order.tracking,
    }


@tool
def update_customer_preferences(customer_id: str, preferences: dict) -> dict:
    """Update a customer's preferences.

    Args:
        customer_id: The customer's unique identifier.
        preferences: Dictionary of preferences to update.

    Returns:
        Success message or error.
    """
    customer = Customer.sync_get(pk=f"CUSTOMER#{customer_id}", sk="PROFILE")

    if not customer:
        return {"error": f"Customer {customer_id} not found"}

    customer.sync_update(**preferences)
    return {"success": True, "message": "Preferences updated"}


# Create the agent with tools
agent = Agent(
    model="us.anthropic.claude-sonnet-4-20250514-v1:0",
    tools=[
        get_customer_by_email,
        get_customer_by_id,
        get_recent_orders,
        get_order_status,
        update_customer_preferences,
    ],
    system_prompt="""You are a helpful customer support agent.
You can look up customer information and order status.
Always be polite and helpful. If you can't find information, say so clearly.""",
)


# Example usage
if __name__ == "__main__":

    def create_tables():
        """Create DynamoDB tables if they don't exist."""
        if not client.table_exists("customers"):
            client.create_table(
                table_name="customers",
                hash_key=("pk", "S"),
                range_key=("sk", "S"),
                wait=True,
            )
            print("Table 'customers' created!")

        if not client.table_exists("orders"):
            client.create_table(
                table_name="orders",
                hash_key=("pk", "S"),
                range_key=("sk", "S"),
                wait=True,
            )
            print("Table 'orders' created!")

    def seed_data():
        """Insert sample customers and orders for testing."""
        sample_customers = [
            Customer(
                pk="CUSTOMER#001",
                sk="PROFILE",
                email="john@example.com",
                name="John Smith",
            ),
            Customer(
                pk="CUSTOMER#002",
                sk="PROFILE",
                email="maria@example.com",
                name="Maria Garcia",
            ),
        ]

        sample_orders = [
            Order(
                pk="CUSTOMER#001",
                sk="ORDER#2025-01-05T10:30:00",
                order_id="ORD-1001",
                status="shipped",
                tracking="TRK123456789",
                total=149.99,
            ),
            Order(
                pk="CUSTOMER#001",
                sk="ORDER#2025-01-03T14:20:00",
                order_id="ORD-1000",
                status="delivered",
                tracking="TRK987654321",
                total=79.50,
            ),
            Order(
                pk="CUSTOMER#002",
                sk="ORDER#2025-01-04T09:15:00",
                order_id="ORD-1002",
                status="processing",
                tracking=None,
                total=299.00,
            ),
        ]

        for customer in sample_customers:
            customer.sync_save()
        for order in sample_orders:
            order.sync_save()

        print("Sample data inserted!")

    # Create tables and seed data
    create_tables()
    seed_data()

    # Run the agent
    response = agent("What's the status of John's last order? His email is john@example.com")
    print(response)
