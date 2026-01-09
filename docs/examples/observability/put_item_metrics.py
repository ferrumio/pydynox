from pydynox import DynamoDBClient

client = DynamoDBClient()

# put_item returns OperationMetrics directly
metrics = client.put_item("users", {"pk": "USER#1", "sk": "PROFILE", "name": "John"})

print(metrics.duration_ms)  # 8.2
print(metrics.consumed_wcu)  # 1.0

# Same for delete_item and update_item
metrics = client.delete_item("users", {"pk": "USER#1", "sk": "PROFILE"})
print(metrics.duration_ms)
