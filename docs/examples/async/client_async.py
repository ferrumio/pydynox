"""Client async operations (async is default - no prefix needed)."""

from pydynox import DynamoDBClient


async def main():
    client = DynamoDBClient()

    # Get item
    await client.get_item("users", {"pk": "USER#123", "sk": "PROFILE"})

    # Put item
    await client.put_item("users", {"pk": "USER#123", "name": "John"})

    # Update item
    await client.update_item(
        "users",
        {"pk": "USER#123", "sk": "PROFILE"},
        updates={"name": "Jane"},
    )

    # Delete item
    await client.delete_item("users", {"pk": "USER#123", "sk": "PROFILE"})
