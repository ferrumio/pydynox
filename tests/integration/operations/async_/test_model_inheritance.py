"""Integration tests for model inheritance."""

from __future__ import annotations

import pytest
from pydynox import Model, ModelConfig
from pydynox.attributes import BooleanAttribute, StringAttribute


# Base class without Model metaclass
class AuditBase:
    created_by = StringAttribute()


# Model using base class
class AuditedUser(Model, AuditBase):
    model_config = ModelConfig(table="audited_users")
    pk = StringAttribute(partition_key=True)
    name = StringAttribute()


# Discriminator models
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


@pytest.fixture(autouse=True)
def setup_memory_backend(pydynox_memory_backend):
    """Auto-use fixture to set up memory backend for all tests."""
    pass


async def test_base_class_attributes_saved():
    """Base class attributes should be saved to DynamoDB."""
    user = AuditedUser(pk="USER#1", name="John", created_by="admin")
    await user.save()

    loaded = await AuditedUser.get(pk="USER#1")
    assert loaded is not None
    assert loaded.created_by == "admin"
    assert loaded.name == "John"


async def test_discriminator_auto_set_on_save():
    """Discriminator field should be auto-set when saving."""
    dog = Dog(pk="ANIMAL#1", name="Rex", breed="Labrador")
    await dog.save()

    # Get raw item to verify _type was saved
    loaded = await Animal.get(pk="ANIMAL#1")
    assert loaded is not None
    assert loaded._type == "Dog"


async def test_get_returns_correct_subclass():
    """Getting from parent class should return correct subclass."""
    # Save a dog
    dog = Dog(pk="ANIMAL#1", name="Rex", breed="Labrador")
    await dog.save()

    # Save a cat
    cat = Cat(pk="ANIMAL#2", name="Whiskers", indoor=True)
    await cat.save()

    # Get from Animal - should return Dog
    loaded_dog = await Animal.get(pk="ANIMAL#1")
    assert isinstance(loaded_dog, Dog)
    assert loaded_dog.breed == "Labrador"

    # Get from Animal - should return Cat
    loaded_cat = await Animal.get(pk="ANIMAL#2")
    assert isinstance(loaded_cat, Cat)
    assert loaded_cat.indoor is True


async def test_query_returns_correct_subclasses():
    """Query should return correct subclasses."""
    # Save multiple animals
    await Dog(pk="ANIMAL#1", name="Rex", breed="Labrador").save()
    await Cat(pk="ANIMAL#2", name="Whiskers", indoor=True).save()
    await Dog(pk="ANIMAL#3", name="Max", breed="Poodle").save()

    # Scan all animals
    results = Animal.scan()
    items = [item async for item in results]

    assert len(items) == 3

    dogs = [a for a in items if isinstance(a, Dog)]
    cats = [a for a in items if isinstance(a, Cat)]

    assert len(dogs) == 2
    assert len(cats) == 1
