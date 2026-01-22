from pydynox import DynamoDBClient

client = DynamoDBClient()

# Read multiple items atomically
items = client.transact_get(
    [
        {"table": "users", "key": {"pk": "USER#1", "sk": "PROFILE"}},
        {"table": "orders", "key": {"pk": "ORDER#1", "sk": "DETAILS"}},
        {"table": "inventory", "key": {"pk": "ITEM#1"}},
    ]
)

# items[0] = user, items[1] = order, items[2] = inventory
# Returns None for items that don't exist
for item in items:
    if item:
        print(item)
