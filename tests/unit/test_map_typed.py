"""Tests for typed MapAttribute with Pydantic models and dataclasses."""

import dataclasses
from typing import Any

from pydynox import Model, ModelConfig
from pydynox.attributes import MapAttribute, StringAttribute
from pydynox.testing import MemoryBackend


@dataclasses.dataclass
class Address:
    street: str
    city: str
    zip: str


class User(Model):
    model_config = ModelConfig(table="users")
    pk = StringAttribute(partition_key=True)
    address = MapAttribute(Address)


class Profile(Model):
    model_config = ModelConfig(table="profiles")
    pk = StringAttribute(partition_key=True)
    metadata = MapAttribute()


# --- Typed MapAttribute with dataclass ---


def test_typed_map_model_init():
    """Typed MapAttribute accepts dataclass on init."""
    # WHEN we create a model with a typed map attribute
    user = User(pk="USER#1", address=Address(street="123 Main St", city="NYC", zip="10001"))

    # THEN the value should be the dataclass instance
    assert user.address == Address(street="123 Main St", city="NYC", zip="10001")
    assert user.address.city == "NYC"


def test_typed_map_model_none():
    """Typed MapAttribute defaults to None when not provided."""
    # WHEN we create a model without setting the map attribute
    user = User(pk="USER#1")

    # THEN it should be None
    assert user.address is None


def test_typed_map_to_dict():
    """to_dict serializes typed map to dict (not JSON string)."""
    # GIVEN a model with typed map
    user = User(pk="USER#1", address=Address(street="123 Main St", city="NYC", zip="10001"))

    # WHEN we convert to dict
    result = user.to_dict()

    # THEN address should be a dict (DynamoDB M type, not a JSON string)
    assert result["address"] == {"street": "123 Main St", "city": "NYC", "zip": "10001"}


def test_typed_map_from_dict():
    """from_dict deserializes dict to typed model."""
    # GIVEN raw DynamoDB data with map dict
    data = {"pk": "USER#1", "address": {"street": "123 Main St", "city": "NYC", "zip": "10001"}}

    # WHEN we create from dict
    user = User.from_dict(data)

    # THEN address should be the dataclass instance
    assert user.address == Address(street="123 Main St", city="NYC", zip="10001")


# --- Backward compatibility ---


def test_untyped_map_still_works():
    """Untyped MapAttribute works exactly as before."""
    # GIVEN a model with untyped map
    profile = Profile(pk="PROF#1", metadata={"theme": "dark", "lang": "en"})

    # THEN it should be a plain dict
    assert profile.metadata == {"theme": "dark", "lang": "en"}

    # AND to_dict should return the dict directly
    result = profile.to_dict()
    assert result["metadata"] == {"theme": "dark", "lang": "en"}


def test_untyped_map_from_dict():
    """Untyped MapAttribute from_dict returns plain dict."""
    data = {"pk": "PROF#1", "metadata": {"theme": "dark"}}
    profile = Profile.from_dict(data)

    assert profile.metadata == {"theme": "dark"}
    assert isinstance(profile.metadata, dict)


# --- In-place mutation tracking ---


def test_map_snapshots_built_on_from_dict():
    """from_dict should build snapshots for typed MapAttributes."""
    data = {"pk": "USER#1", "address": {"street": "123 Main St", "city": "NYC", "zip": "10001"}}
    user = User.from_dict(data)

    # THEN _json_snapshots should contain the typed attribute
    assert "address" in user._json_snapshots


def test_map_snapshots_empty_for_untyped():
    """Untyped MapAttribute should not produce snapshots."""
    data = {"pk": "PROF#1", "metadata": {"theme": "dark"}}
    profile = Profile.from_dict(data)

    # THEN _json_snapshots should be empty
    assert profile._json_snapshots == {}


def test_detect_inplace_map_mutation():
    """_detect_json_mutations catches in-place changes on typed MapAttribute."""
    data = {"pk": "USER#1", "address": {"street": "123 Main St", "city": "NYC", "zip": "10001"}}
    user = User.from_dict(data)

    # GIVEN the instance is clean
    assert user.is_dirty is False

    # WHEN we mutate the address in-place
    user.address.city = "Brooklyn"

    # AND we run mutation detection
    user._detect_json_mutations()

    # THEN the change should be detected
    assert user.is_dirty is True
    assert "address" in user.changed_fields


def test_no_false_positive_without_map_mutation():
    """_detect_json_mutations should not flag unchanged MapAttributes."""
    data = {"pk": "USER#1", "address": {"street": "123 Main St", "city": "NYC", "zip": "10001"}}
    user = User.from_dict(data)

    # WHEN we run detection without any mutation
    user._detect_json_mutations()

    # THEN it should remain clean
    assert user.is_dirty is False


def test_detect_map_mutation_with_none_value():
    """_detect_json_mutations handles None address correctly."""
    data: dict[str, Any] = {"pk": "USER#1"}
    user = User.from_dict(data)

    # WHEN address is None and we detect mutations
    user._detect_json_mutations()

    # THEN it should remain clean
    assert user.is_dirty is False


@MemoryBackend()
def test_inplace_map_mutation_detected_on_save():
    """sync_save detects in-place mutations on typed MapAttributes."""
    # GIVEN a saved model with typed map
    user = User(pk="USER#1", address=Address(street="123 Main St", city="NYC", zip="10001"))
    user.sync_save()

    # WHEN we load it and mutate in-place
    loaded = User.sync_get(pk="USER#1")
    loaded.address.city = "Brooklyn"

    # AND save again
    loaded.sync_save()

    # THEN the mutation should be persisted
    result = User.sync_get(pk="USER#1")
    assert result.address.city == "Brooklyn"
    assert result.address.street == "123 Main St"


@MemoryBackend()
def test_reset_tracking_rebuilds_map_snapshots():
    """_reset_change_tracking should rebuild snapshots for MapAttributes."""
    user = User(pk="USER#1", address=Address(street="123 Main St", city="NYC", zip="10001"))
    user.sync_save()

    # After save, snapshots should reflect current state
    assert "address" in user._json_snapshots
    assert "NYC" in user._json_snapshots["address"]

    # Mutate and save
    loaded = User.sync_get(pk="USER#1")
    loaded.address.city = "Brooklyn"
    loaded.sync_save()

    # Snapshots should be updated
    assert "Brooklyn" in loaded._json_snapshots["address"]


@MemoryBackend()
def test_assignment_still_tracked_for_typed_map():
    """Full assignment (not in-place) is still tracked via __setattr__."""
    user = User(pk="USER#1", address=Address(street="123 Main St", city="NYC", zip="10001"))
    user.sync_save()

    loaded = User.sync_get(pk="USER#1")
    loaded.address = Address(street="456 Elm St", city="Chicago", zip="60601")

    assert loaded.is_dirty is True
    assert "address" in loaded.changed_fields
