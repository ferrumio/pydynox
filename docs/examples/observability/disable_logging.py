import asyncio
import logging

from pydynox import DynamoDBClient

# Disable pydynox logs completely
logging.getLogger("pydynox").setLevel(logging.CRITICAL)

client = DynamoDBClient()


async def main():
    # No logs will be emitted
    await client.put_item("users", {"pk": "USER#1", "sk": "PROFILE", "name": "John"})
    await client.get_item("users", {"pk": "USER#1", "sk": "PROFILE"})


asyncio.run(main())
