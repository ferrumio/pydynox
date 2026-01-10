"""Example: Table creation with different options."""

from pydynox import DynamoDBClient

client = DynamoDBClient()

# Provisioned capacity (fixed cost, predictable performance)
if not client.table_exists("example_provisioned"):
    client.create_table(
        "example_provisioned",
        hash_key=("pk", "S"),
        billing_mode="PROVISIONED",
        read_capacity=5,
        write_capacity=5,
        wait=True,
    )

# Infrequent access class (cheaper storage, higher read cost)
if not client.table_exists("example_archive"):
    client.create_table(
        "example_archive",
        hash_key=("pk", "S"),
        table_class="STANDARD_INFREQUENT_ACCESS",
        wait=True,
    )

# Verify tables exist
assert client.table_exists("example_provisioned")
assert client.table_exists("example_archive")

# Cleanup
client.delete_table("example_provisioned")
client.delete_table("example_archive")
