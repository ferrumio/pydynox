import asyncio

from pydynox import Model, ModelConfig
from pydynox.attributes import BooleanAttribute, StringAttribute


class Animal(Model):
    model_config = ModelConfig(table="animals")
    pk = StringAttribute(partition_key=True)
    name = StringAttribute()
    _type = StringAttribute(discriminator=True)


class Dog(Animal):
    model_config = ModelConfig(table="animals")
    breed = StringAttribute()


class Cat(Animal):
    model_config = ModelConfig(table="animals")
    indoor = BooleanAttribute()


async def main():
    # Save different animals
    await Dog(pk="ANIMAL#1", name="Rex", breed="Labrador").save()
    await Cat(pk="ANIMAL#2", name="Whiskers", indoor=True).save()
    await Dog(pk="ANIMAL#3", name="Max", breed="Poodle").save()

    # Scan from Animal - returns correct subclasses
    results = Animal.scan()
    items = [item async for item in results]

    dogs = [a for a in items if isinstance(a, Dog)]
    cats = [a for a in items if isinstance(a, Cat)]

    assert len(dogs) == 2
    assert len(cats) == 1

    # Each item has the correct type
    for item in items:
        if isinstance(item, Dog):
            assert hasattr(item, "breed")
        elif isinstance(item, Cat):
            assert hasattr(item, "indoor")


if __name__ == "__main__":
    asyncio.run(main())
