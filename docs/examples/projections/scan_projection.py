import asyncio

from pydynox import Model, ModelConfig
from pydynox.attributes import StringAttribute


class User(Model):
    model_config = ModelConfig(table="users")

    pk = StringAttribute(partition_key=True)
    name = StringAttribute()
    status = StringAttribute()


async def main():
    # Scan with fields - useful for reports or exports
    async for user in User.scan(fields=["pk", "status"]):
        print(user.pk, user.status)


asyncio.run(main())
