"""Get the deleted item back from delete_item."""

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

TABLE = "rv_delete_example"
if not client.sync_table_exists(TABLE):
    client.sync_create_table(TABLE, partition_key=("pk", "S"), sort_key=("sk", "S"), wait=True)

client.sync_put_item(TABLE, {"pk": "USER#1", "sk": "PROFILE", "name": "Alice", "age": 25})

# Delete and get the item that was removed
deleted_item = client.sync_delete_item(
    TABLE,
    {"pk": "USER#1", "sk": "PROFILE"},
    return_values="ALL_OLD",
)

print(f"Deleted: {deleted_item['name']}")  # Alice

# Metrics are available via get_last_metrics()
print(f"Duration: {client.get_last_metrics().duration_ms:.1f}ms")

# If the item didn't exist, deleted_item is None
deleted_item = client.sync_delete_item(
    TABLE,
    {"pk": "USER#GHOST", "sk": "NONE"},
    return_values="ALL_OLD",
)
print(f"Deleted non-existent: {deleted_item}")  # None

client.sync_delete_table(TABLE)
