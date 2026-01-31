"""Unit tests for model inheritance."""

from __future__ import annotations

import pytest
from pydynox import Model, ModelConfig
from pydynox.attributes import BooleanAttribute, NumberAttribute, StringAttribute
from pydynox.client import DynamoDBClient


# Base class without Model metaclass
class TimestampBase:
    created_by = StringAttribute()
    version = NumberAttribute()


# Model using base class
class User(Model, TimestampBase):
    model_config = ModelConfig(table="users", client=DynamoDBClient())
    pk = StringAttribute(partition_key=True)
    name = StringAttribute()


def test_base_class_attributes_collected():
    """Attributes from base class should be in _attributes."""
    assert "created_by" in User._attributes
    assert "version" in User._attributes
    assert "pk" in User._attributes
    assert "name" in User._attributes


def test_base_class_attributes_work():
    """Can set and get base class attributes."""
    user = User(pk="USER#1", name="John", created_by="admin", version=1)
    assert user.created_by == "admin"
    assert user.version == 1


def test_base_class_attributes_in_to_dict():
    """Base class attributes should be in to_dict output."""
    user = User(pk="USER#1", name="John", created_by="admin", version=1)
    data = user.to_dict()
    assert data["created_by"] == "admin"
    assert data["version"] == 1


def test_base_class_attributes_from_dict():
    """Can create model from dict with base class attributes."""
    data = {"pk": "USER#1", "name": "John", "created_by": "admin", "version": 1}
    user = User.from_dict(data)
    assert user.created_by == "admin"
    assert user.version == 1


# Discriminator tests
class Animal(Model):
    model_config = ModelConfig(table="animals", client=DynamoDBClient())
    pk = StringAttribute(partition_key=True)
    name = StringAttribute()
    _type = StringAttribute(discriminator=True)


class Dog(Animal):
    breed = StringAttribute()


class Cat(Animal):
    indoor = BooleanAttribute()


def test_discriminator_registry_populated():
    """Subclasses should be registered in parent's registry."""
    assert "Dog" in Animal._discriminator_registry
    assert "Cat" in Animal._discriminator_registry
    assert Animal._discriminator_registry["Dog"] is Dog
    assert Animal._discriminator_registry["Cat"] is Cat


def test_discriminator_auto_set_on_to_dict():
    """Discriminator field should be auto-set to class name."""
    dog = Dog(pk="ANIMAL#1", name="Rex", breed="Labrador")
    data = dog.to_dict()
    assert data["_type"] == "Dog"


def test_discriminator_auto_set_for_parent():
    """Parent class should also set discriminator."""
    animal = Animal(pk="ANIMAL#2", name="Generic")
    data = animal.to_dict()
    assert data["_type"] == "Animal"


def test_from_dict_returns_correct_subclass():
    """from_dict should return correct subclass based on discriminator."""
    data = {"pk": "ANIMAL#1", "name": "Rex", "breed": "Labrador", "_type": "Dog"}
    animal = Animal.from_dict(data)
    assert isinstance(animal, Dog)
    assert animal.breed == "Labrador"


def test_from_dict_returns_cat():
    """from_dict should return Cat for cat data."""
    data = {"pk": "ANIMAL#2", "name": "Whiskers", "indoor": True, "_type": "Cat"}
    animal = Animal.from_dict(data)
    assert isinstance(animal, Cat)
    assert animal.indoor is True


def test_from_dict_returns_parent_for_unknown_type():
    """from_dict should return parent class for unknown type."""
    data = {"pk": "ANIMAL#3", "name": "Unknown", "_type": "Bird"}
    animal = Animal.from_dict(data)
    assert type(animal) is Animal


def test_from_dict_returns_parent_when_no_type():
    """from_dict should return parent class when no type field."""
    data = {"pk": "ANIMAL#4", "name": "NoType"}
    animal = Animal.from_dict(data)
    assert type(animal) is Animal


def test_subclass_inherits_parent_attributes():
    """Subclass should have all parent attributes."""
    assert "pk" in Dog._attributes
    assert "name" in Dog._attributes
    assert "_type" in Dog._attributes
    assert "breed" in Dog._attributes


def test_subclass_has_own_discriminator_registry():
    """Subclass should have its own registry for further inheritance."""
    assert Dog._discriminator_registry is not None


# Multiple inheritance levels
class GoldenRetriever(Dog):
    is_service_dog = BooleanAttribute()


def test_deep_inheritance():
    """Three levels of inheritance should work."""
    gr = GoldenRetriever(pk="ANIMAL#5", name="Buddy", breed="Golden Retriever", is_service_dog=True)
    data = gr.to_dict()
    assert data["_type"] == "GoldenRetriever"
    assert data["breed"] == "Golden Retriever"
    assert data["is_service_dog"] is True


def test_deep_inheritance_from_dict():
    """from_dict should work with deep inheritance."""
    data = {
        "pk": "ANIMAL#5",
        "name": "Buddy",
        "breed": "Golden Retriever",
        "is_service_dog": True,
        "_type": "GoldenRetriever",
    }
    # Query from Animal should return GoldenRetriever
    animal = Animal.from_dict(data)
    assert isinstance(animal, GoldenRetriever)
    assert animal.is_service_dog is True


@pytest.mark.parametrize(
    "data,expected_type",
    [
        pytest.param(
            {"pk": "1", "name": "Rex", "breed": "Lab", "_type": "Dog"},
            Dog,
            id="dog",
        ),
        pytest.param(
            {"pk": "2", "name": "Whiskers", "indoor": True, "_type": "Cat"},
            Cat,
            id="cat",
        ),
        pytest.param(
            {"pk": "3", "name": "Generic", "_type": "Animal"},
            Animal,
            id="animal",
        ),
    ],
)
def test_from_dict_type_resolution(data, expected_type):
    """from_dict should resolve to correct type."""
    result = Animal.from_dict(data)
    assert type(result) is expected_type
