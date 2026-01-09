from pydynox import DynamoDBClient

client = DynamoDBClient()

# get_item returns a dict with .metrics
item = client.get_item("users", {"pk": "USER#1", "sk": "PROFILE"})

if item:
    print(item["name"])  # Works like a normal dict
    print(item.metrics.duration_ms)  # 12.1
    print(item.metrics.consumed_rcu)  # 0.5
