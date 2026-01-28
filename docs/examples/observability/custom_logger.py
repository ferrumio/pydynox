import asyncio

from aws_lambda_powertools import Logger
from pydynox import DynamoDBClient, set_logger

# With AWS Lambda Powertools
logger = Logger()
set_logger(logger)


async def main():
    # Now all pydynox logs go through Powertools
    client = DynamoDBClient()
    await client.put_item("users", {"pk": "USER#1", "sk": "PROFILE", "name": "John"})


asyncio.run(main())
