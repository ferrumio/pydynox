import asyncio

from pydynox import DynamoDBClient, Transaction
from pydynox.exceptions import TransactionCanceledException

client = DynamoDBClient()


async def safe_transfer():
    try:
        async with Transaction(client) as tx:
            tx.put("users", {"pk": "USER#1", "name": "John"})
            tx.put("orders", {"pk": "ORDER#1", "user": "USER#1"})
    except TransactionCanceledException as e:
        print(f"Transaction canceled: {e}")
    except Exception as e:
        print(f"Transaction failed: {e}")


asyncio.run(safe_transfer())
