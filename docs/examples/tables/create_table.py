"""Example: Create tables with client."""

from pydynox import DynamoDBClient

client = DynamoDBClient()

# Simple table with hash key only
if not client.table_exists("example_users"):
    client.create_table(
        "example_users",
        hash_key=("pk", "S"),
        wait=True,
    )

# Table with hash key and range key
if not client.table_exists("example_orders"):
    client.create_table(
        "example_orders",
        hash_key=("pk", "S"),
        range_key=("sk", "S"),
        wait=True,
    )

# Verify tables exist
assert client.table_exists("example_users")
assert client.table_exists("example_orders")

# Cleanup
client.delete_table("example_users")
client.delete_table("example_orders")
