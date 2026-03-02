"""Get the old item when overwriting with put_item."""

import os

from pydynox import DynamoDBClient, set_default_client

endpoint = os.environ.get("AWS_ENDPOINT_URL", "http://localhost:4566")

client = DynamoDBClient(
    endpoint_url=endpoint,
    region="us-east-1",
    access_key="testing",
    secret_key="testing",
)
set_default_client(client)

TABLE = "rv_put_example"
if not client.sync_table_exists(TABLE):
    client.sync_create_table(TABLE, partition_key=("pk", "S"), sort_key=("sk", "S"), wait=True)

# Save an item
client.sync_put_item(TABLE, {"pk": "USER#1", "sk": "PROFILE", "name": "Alice", "age": 25})

# Overwrite it and get the old version back
old_item = client.sync_put_item(
    TABLE,
    {"pk": "USER#1", "sk": "PROFILE", "name": "Bob", "age": 30},
    return_values="ALL_OLD",
)

print(f"Old name: {old_item['name']}")  # Alice
print(f"Old age: {old_item['age']}")  # 25

# Metrics are available via get_last_metrics()
print(f"Duration: {client.get_last_metrics().duration_ms:.1f}ms")

# If the item didn't exist before, old_item is None
new_item = {"pk": "USER#NEW", "sk": "PROFILE", "name": "Charlie"}
old_item = client.sync_put_item(TABLE, new_item, return_values="ALL_OLD")
print(f"Old item for new key: {old_item}")  # None

client.sync_delete_table(TABLE)
