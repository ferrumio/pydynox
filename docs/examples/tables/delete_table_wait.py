"""Example: Delete a table and wait until it is gone (sync version)."""

from pydynox import DynamoDBClient

client = DynamoDBClient()

client.sync_create_table("example_temp", partition_key=("pk", "S"), wait=True)

# Returns after the table no longer exists
client.sync_delete_table("example_temp", wait=True, timeout_seconds=60)
assert not client.sync_table_exists("example_temp")

# The name is free again, so the table can be recreated
client.sync_create_table("example_temp", partition_key=("pk", "S"), wait=True)

# Cleanup
client.sync_delete_table("example_temp", wait=True)
