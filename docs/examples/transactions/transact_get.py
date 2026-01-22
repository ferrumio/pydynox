from pydynox import DynamoDBClient

client = DynamoDBClient()

# First, save some items to read
client.put_item("users", {"pk": "USER#1", "sk": "PROFILE", "name": "John"})
client.put_item("orders", {"pk": "ORDER#1", "sk": "DETAILS", "total": 100})

# Read multiple items atomically
items = client.transact_get(
    [
        {"table": "users", "key": {"pk": "USER#1", "sk": "PROFILE"}},
        {"table": "orders", "key": {"pk": "ORDER#1", "sk": "DETAILS"}},
    ]
)

# items[0] = user, items[1] = order
# Returns None for items that don't exist
for item in items:
    if item:
        print(item.get("name") or item.get("total"))
