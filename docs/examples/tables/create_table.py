"""Example: Create tables with client (sync version)."""

from pydynox import DynamoDBClient

client = DynamoDBClient()

# Simple table with hash key only
if not client.sync_table_exists("example_users"):
    client.sync_create_table(
        "example_users",
        hash_key=("pk", "S"),
        wait=True,
    )

# Table with hash key and range key
if not client.sync_table_exists("example_orders"):
    client.sync_create_table(
        "example_orders",
        hash_key=("pk", "S"),
        range_key=("sk", "S"),
        wait=True,
    )

# Verify tables exist
assert client.sync_table_exists("example_users")
assert client.sync_table_exists("example_orders")

# Cleanup
client.sync_delete_table("example_users")
client.sync_delete_table("example_orders")
