from pydynox import DynamoDBClient

client = DynamoDBClient()

# Do some operations
client.put_item("users", {"pk": "USER#1", "sk": "PROFILE", "name": "John"})
client.put_item("users", {"pk": "USER#2", "sk": "PROFILE", "name": "Jane"})
client.get_item("users", {"pk": "USER#1", "sk": "PROFILE"})

# Get total metrics
total = client.get_total_metrics()
print(total.total_rcu)  # 0.5
print(total.total_wcu)  # 2.0
print(total.operation_count)  # 3
print(total.put_count)  # 2
print(total.get_count)  # 1
