from pydynox import AsyncBatchWriter, DynamoDBClient, Model, ModelConfig
from pydynox.attributes import NumberAttribute, StringAttribute

client = DynamoDBClient()


class User(Model):
    model_config = ModelConfig(table="users", client=client)
    pk = StringAttribute(hash_key=True)
    sk = StringAttribute(range_key=True)
    name = StringAttribute()
    age = NumberAttribute()


async def main():
    # Async batch write with context manager
    async with AsyncBatchWriter(client, "users") as batch:
        for i in range(100):
            batch.put({"pk": f"USER#{i}", "sk": "PROFILE", "name": f"User {i}"})

    # Mix puts and deletes
    async with AsyncBatchWriter(client, "users") as batch:
        batch.put({"pk": "USER#1", "sk": "PROFILE", "name": "John"})
        batch.put({"pk": "USER#2", "sk": "PROFILE", "name": "Jane"})
        batch.delete({"pk": "USER#3", "sk": "PROFILE"})

    # Async batch get - client level
    keys = [
        {"pk": "USER#1", "sk": "PROFILE"},
        {"pk": "USER#2", "sk": "PROFILE"},
    ]
    items = await client.async_batch_get("users", keys)
    for item in items:
        print(item["name"])

    # Async batch get - model level
    users = await User.async_batch_get(keys)
    for user in users:
        print(user.name, user.age)

    # Return as dicts for better performance
    users_dict = await User.async_batch_get(keys, as_dict=True)
    for user in users_dict:
        print(user["name"])
