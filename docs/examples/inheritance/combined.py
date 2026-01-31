import asyncio
from datetime import datetime, timezone

from pydynox import Model, ModelConfig
from pydynox.attributes import BooleanAttribute, DatetimeAttribute, StringAttribute


# Base class with shared attributes
class AuditBase:
    created_at = DatetimeAttribute()
    created_by = StringAttribute()


# Parent model with discriminator
class Animal(Model, AuditBase):
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
    now = datetime.now(timezone.utc)

    # Dog has both base class attributes and discriminator
    dog = Dog(
        pk="ANIMAL#1",
        name="Rex",
        breed="Labrador",
        created_at=now,
        created_by="admin",
    )
    await dog.save()

    # Load from Animal - returns Dog with all attributes
    loaded = await Animal.get(pk="ANIMAL#1")
    if loaded:
        assert isinstance(loaded, Dog)
        assert loaded.breed == "Labrador"
        assert loaded.created_by == "admin"
        assert loaded._type == "Dog"


if __name__ == "__main__":
    asyncio.run(main())
