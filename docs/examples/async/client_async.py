from pydynox import DynamoDBClient


async def main():
    client = DynamoDBClient()

    # Get item
    await client.async_get_item("users", {"pk": "USER#123", "sk": "PROFILE"})

    # Put item
    await client.async_put_item("users", {"pk": "USER#123", "name": "John"})

    # Update item
    await client.async_update_item(
        "users",
        {"pk": "USER#123", "sk": "PROFILE"},
        updates={"name": "Jane"},
    )

    # Delete item
    await client.async_delete_item("users", {"pk": "USER#123", "sk": "PROFILE"})
