"""Retry the same stock reservation without decrementing inventory twice."""

import asyncio
from uuid import uuid4

from pydynox import DynamoDBClient, Transaction


async def main() -> None:
    client = DynamoDBClient()
    key = {"pk": "PRODUCT#IDEMPOTENCY#ASYNC"}
    await client.put_item("products", {**key, "stock": 10})

    # Create once per logical reservation; store it if retries can outlive this process.
    token = str(uuid4())

    # Two separate calls with the same token and payload apply the write only once.
    for _ in range(2):
        async with Transaction(client, client_request_token=token) as tx:
            tx.update(
                "products",
                key,
                update_expression="SET #stock = #stock - :quantity",
                condition_expression="#stock >= :quantity",
                expression_attribute_names={"#stock": "stock"},
                expression_attribute_values={":quantity": 1},
            )

    item = await client.get_item("products", key, consistent_read=True)
    assert item is not None
    assert item["stock"] == 9
    print(item["stock"])  # 9


asyncio.run(main())
