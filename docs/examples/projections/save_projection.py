"""Save a model loaded with a projection."""

import asyncio

from pydynox import DynamoDBClient, Model, ModelConfig
from pydynox.attributes import NumberAttribute, StringAttribute

client = DynamoDBClient()


class User(Model):
    model_config = ModelConfig(table="users", client=client)
    pk = StringAttribute(partition_key=True)
    sk = StringAttribute(sort_key=True)
    name = StringAttribute(required=True)
    email = StringAttribute()
    age = NumberAttribute(default=0)


async def main():
    await User(pk="USER#42", sk="PROFILE", name="Ann", email="ann@example.com", age=30).save()

    # Load only the keys and email
    user = await User.query(partition_key="USER#42", fields=["pk", "sk", "email"]).first()
    assert user is not None

    # Fields you did not fetch are None. No default, no required check.
    assert user.name is None
    assert user.age is None

    # save() only writes the fields you change, so name and age are kept
    user.email = "ann@new.example.com"
    await user.save()

    stored = await User.get(pk="USER#42", sk="PROFILE")
    assert stored is not None
    assert stored.name == "Ann"
    assert stored.age == 30
    assert stored.email == "ann@new.example.com"


asyncio.run(main())
