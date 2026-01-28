"""SDK debug logging example."""

import asyncio
import logging

from pydynox import DynamoDBClient, set_logger

# Create a logger
logger = logging.getLogger("pydynox")
logger.setLevel(logging.DEBUG)

# Enable SDK debug logs
set_logger(logger, sdk_debug=True)


async def main():
    # Now you'll see detailed AWS SDK logs
    client = DynamoDBClient()
    await client.get_item("users", {"pk": "USER#1"})


asyncio.run(main())
