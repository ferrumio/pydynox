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


# GoldenRetriever extends Dog, which extends Animal
class GoldenRetriever(Dog):
    model_config = ModelConfig(table="animals")
    is_service_dog = BooleanAttribute()


async def main():
    # Save a GoldenRetriever
    buddy = GoldenRetriever(
        pk="ANIMAL#1",
        name="Buddy",
        breed="Golden Retriever",
        is_service_dog=True,
    )
    await buddy.save()

    # Get from Animal - returns GoldenRetriever
    loaded = await Animal.get(pk="ANIMAL#1")
    if loaded:
        assert isinstance(loaded, GoldenRetriever)
        assert loaded.is_service_dog is True
        assert loaded.breed == "Golden Retriever"
        assert loaded._type == "GoldenRetriever"


if __name__ == "__main__":
    asyncio.run(main())
