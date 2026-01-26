from pydynox import BatchWriter, DynamoDBClient

client = DynamoDBClient()


async def main():
    # Batch write (async by default) - items are sent in groups of 25
    async with BatchWriter(client, "users") as batch:
        for i in range(100):
            batch.put({"pk": f"USER#{i}", "sk": "PROFILE", "name": f"User {i}"})

    # Mix puts and deletes
    async with BatchWriter(client, "users") as batch:
        batch.put({"pk": "USER#1", "sk": "PROFILE", "name": "John"})
        batch.put({"pk": "USER#2", "sk": "PROFILE", "name": "Jane"})
        batch.delete({"pk": "USER#3", "sk": "PROFILE"})
