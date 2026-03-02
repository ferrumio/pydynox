"""Get item data back after an update_item call."""

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

TABLE = "rv_update_example"
if not client.sync_table_exists(TABLE):
    client.sync_create_table(TABLE, partition_key=("pk", "S"), sort_key=("sk", "S"), wait=True)

client.sync_put_item(
    TABLE, {"pk": "USER#1", "sk": "PROFILE", "name": "Alice", "age": 25, "status": "active"}
)

# ALL_NEW: get the full item after the update
item = client.sync_update_item(
    TABLE,
    {"pk": "USER#1", "sk": "PROFILE"},
    updates={"name": "Bob", "age": 30},
    return_values="ALL_NEW",
)
print(f"Full item after update: {item}")
# {'pk': 'USER#1', 'sk': 'PROFILE', 'name': 'Bob', 'age': 30, 'status': 'active'}

# UPDATED_NEW: only the fields that changed (new values)
changed = client.sync_update_item(
    TABLE,
    {"pk": "USER#1", "sk": "PROFILE"},
    updates={"age": 35},
    return_values="UPDATED_NEW",
)
print(f"Changed fields (new): {changed}")
# {'age': 35}

# ALL_OLD: the full item before the update
old = client.sync_update_item(
    TABLE,
    {"pk": "USER#1", "sk": "PROFILE"},
    updates={"name": "Charlie"},
    return_values="ALL_OLD",
)
print(f"Full item before update: {old}")
# {'pk': 'USER#1', 'sk': 'PROFILE', 'name': 'Bob', 'age': 35, 'status': 'active'}

# UPDATED_OLD: only the fields that changed (old values)
old_changed = client.sync_update_item(
    TABLE,
    {"pk": "USER#1", "sk": "PROFILE"},
    updates={"age": 40},
    return_values="UPDATED_OLD",
)
print(f"Changed fields (old): {old_changed}")
# {'age': 35}

# Metrics are always available via get_last_metrics()
print(f"Duration: {client.get_last_metrics().duration_ms:.1f}ms")

client.sync_delete_table(TABLE)
