"""PartiQL with Model - returns typed instances."""

import asyncio

from pydynox import Model, ModelConfig
from pydynox.attributes import NumberAttribute, StringAttribute


class User(Model):
    model_config = ModelConfig(table="users")
    pk = StringAttribute(hash_key=True)
    sk = StringAttribute(range_key=True)
    name = StringAttribute()
    age = NumberAttribute()


async def main():
    # Returns list of User instances (typed)
    users = await User.execute_statement(
        "SELECT * FROM users WHERE pk = ?",
        parameters=["USER#123"],
    )

    for user in users:
        print(user.name)  # IDE knows this is a string
        print(user.age)  # IDE knows this is a number


asyncio.run(main())
