import asyncio

from pydynox import Model, ModelConfig
from pydynox.attributes import StringAttribute


# Using item_type instead of _type
class Entity(Model):
    model_config = ModelConfig(table="entities")
    pk = StringAttribute(partition_key=True)
    item_type = StringAttribute(discriminator=True)


class Person(Entity):
    model_config = ModelConfig(table="entities")
    name = StringAttribute()


class Company(Entity):
    model_config = ModelConfig(table="entities")
    company_name = StringAttribute()


async def main():
    person = Person(pk="ENTITY#1", name="John")
    await person.save()

    # item_type is "Person"
    loaded = await Entity.get(pk="ENTITY#1")
    if loaded:
        assert loaded.item_type == "Person"
        assert isinstance(loaded, Person)


if __name__ == "__main__":
    asyncio.run(main())
