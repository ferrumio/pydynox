"""Sync stock reservation with an explicit request token."""

from uuid import uuid4

from pydynox import DynamoDBClient, SyncTransaction

client = DynamoDBClient()
key = {"pk": "PRODUCT#IDEMPOTENCY#SYNC"}
client.sync_put_item("products", {**key, "stock": 10})

# Create once per logical reservation; reuse it for retries.
token = str(uuid4())

for _ in range(2):
    with SyncTransaction(client, client_request_token=token) as tx:
        tx.update(
            "products",
            key,
            update_expression="SET #stock = #stock - :quantity",
            condition_expression="#stock >= :quantity",
            expression_attribute_names={"#stock": "stock"},
            expression_attribute_values={":quantity": 1},
        )

item = client.sync_get_item("products", key, consistent_read=True)
assert item is not None
assert item["stock"] == 9
print(item["stock"])  # 9
