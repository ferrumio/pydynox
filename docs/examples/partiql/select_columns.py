"""PartiQL SELECT specific columns."""

import asyncio

from pydynox import DynamoDBClient


async def main():
    client = DynamoDBClient()

    # Select only name and age columns
    result = await client.execute_statement(
        "SELECT name, age FROM users WHERE pk = ? AND sk = ?",
        parameters=["USER#1", "PROFILE"],
    )

    for item in result:
        print(f"{item['name']} is {item['age']} years old")


asyncio.run(main())
