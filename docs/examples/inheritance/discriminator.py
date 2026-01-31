import asyncio

from pydynox import Model, ModelConfig
from pydynox.attributes import BooleanAttribute, StringAttribute


# Parent model with discriminator field
class Animal(Model):
    model_config = ModelConfig(table="animals")
    pk = StringAttribute(partition_key=True)
    name = StringAttribute()
    _type = StringAttribute(discriminator=True)  # Marks this as discriminator


# Subclasses - each gets its own attributes
class Dog(Animal):
    model_config = ModelConfig(table="animals")
    breed = StringAttribute()


class Cat(Animal):
    model_config = ModelConfig(table="animals")
    indoor = BooleanAttribute()


async def main():
    # Save a dog - _type is set automatically to "Dog"
    dog = Dog(pk="ANIMAL#1", name="Rex", breed="Labrador")
    await dog.save()

    # Save a cat - _type is set automatically to "Cat"
    cat = Cat(pk="ANIMAL#2", name="Whiskers", indoor=True)
    await cat.save()

    # Get from Animal - returns the correct subclass
    loaded = await Animal.get(pk="ANIMAL#1")
    if loaded:
        assert isinstance(loaded, Dog)
        assert loaded.breed == "Labrador"

    loaded = await Animal.get(pk="ANIMAL#2")
    if loaded:
        assert isinstance(loaded, Cat)
        assert loaded.indoor is True


if __name__ == "__main__":
    asyncio.run(main())
