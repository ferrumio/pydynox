from pydynox import DynamoDBClient

client = DynamoDBClient()

# Nested attributes use dot notation
item = client.get_item(
    "users",
    {"pk": "USER#1"},
    projection=["name", "address.city", "address.zip"],
)
# Returns: {"pk": "USER#1", "name": "John", "address": {"city": "NYC", "zip": "10001"}}
print(item)
