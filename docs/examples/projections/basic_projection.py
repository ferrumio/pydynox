import asyncio

from pydynox import Model, ModelConfig
from pydynox.attributes import NumberAttribute, StringAttribute


class User(Model):
    model_config = ModelConfig(table="users")

    pk = StringAttribute(hash_key=True)
    name = StringAttribute()
    email = StringAttribute()
    age = NumberAttribute()
    address = StringAttribute()


async def main():
    # Query with specific fields - only fetches name and email
    async for user in User.query(hash_key="USER#123", fields=["name", "email"]):
        print(user.name, user.email)
        # user.age and user.address will be None


asyncio.run(main())
