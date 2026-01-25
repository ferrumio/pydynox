"""Example: Table creation with different options (sync version)."""

from pydynox import DynamoDBClient

client = DynamoDBClient()

# Provisioned capacity (fixed cost, predictable performance)
if not client.sync_table_exists("example_provisioned"):
    client.sync_create_table(
        "example_provisioned",
        hash_key=("pk", "S"),
        billing_mode="PROVISIONED",
        read_capacity=5,
        write_capacity=5,
        wait=True,
    )

# Infrequent access class (cheaper storage, higher read cost)
if not client.sync_table_exists("example_archive"):
    client.sync_create_table(
        "example_archive",
        hash_key=("pk", "S"),
        table_class="STANDARD_INFREQUENT_ACCESS",
        wait=True,
    )

# Verify tables exist
assert client.sync_table_exists("example_provisioned")
assert client.sync_table_exists("example_archive")

# Cleanup
client.sync_delete_table("example_provisioned")
client.sync_delete_table("example_archive")
