from pydynox import BatchWriter, DynamoDBClient

client = DynamoDBClient()

# Batch write - items are sent in groups of 25
with BatchWriter(client, "users") as batch:
    for i in range(100):
        batch.put({"pk": f"USER#{i}", "name": f"User {i}"})

# Mix puts and deletes
with BatchWriter(client, "users") as batch:
    batch.put({"pk": "USER#1", "name": "John"})
    batch.put({"pk": "USER#2", "name": "Jane"})
    batch.delete({"pk": "USER#3"})
