from pydynox import DynamoDBClient, SyncTransaction

client = DynamoDBClient()

with SyncTransaction(client) as tx:
    tx.put("users", {"pk": "USER#1", "sk": "PROFILE", "name": "John"})
    tx.put("orders", {"pk": "ORDER#1", "sk": "DETAILS", "user": "USER#1"})

# Direct client method
items = client.sync_transact_get(
    [
        {"table": "users", "key": {"pk": "USER#1", "sk": "PROFILE"}},
    ]
)
