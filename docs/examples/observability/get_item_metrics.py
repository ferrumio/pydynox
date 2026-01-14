from pydynox import DynamoDBClient

client = DynamoDBClient()

# get_item returns a plain dict
item = client.get_item("users", {"pk": "USER#1", "sk": "PROFILE"})

if item:
    print(item["name"])  # Works like a normal dict

# Access metrics via client._last_metrics
print(client._last_metrics.duration_ms)  # 12.1
print(client._last_metrics.consumed_rcu)  # 0.5
