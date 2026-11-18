"""Tests for typed MapAttribute with Pydantic models and dataclasses."""

import dataclasses
from typing import Any

import pytest
from pydynox import Model, ModelConfig
from pydynox.attributes import MapAttribute, StringAttribute
from pydynox.testing import MemoryBackend


@dataclasses.dataclass
class Address:
    street: str
    city: str
    zip: str


SAMPLE_ADDRESS = Address(street="123 Main St", city="NYC", zip="10001")
SAMPLE_ADDRESS_DICT = {"street": "123 Main St", "city": "NYC", "zip": "10001"}


class User(Model):
    model_config = ModelConfig(table="users")
    pk = StringAttribute(partition_key=True)
    address = MapAttribute(Address)


class Profile(Model):
    model_config = ModelConfig(table="profiles")
    pk = StringAttribute(partition_key=True)
    metadata = MapAttribute()


def _user_with_address() -> User:
    return User(pk="USER#1", address=SAMPLE_ADDRESS)


def _user_dict() -> dict[str, Any]:
    return {"pk": "USER#1", "address": SAMPLE_ADDRESS_DICT}


# --- Typed MapAttribute with dataclass ---


def test_typed_map_model_init():
    """Typed MapAttribute accepts dataclass on init."""
    user = _user_with_address()

    assert user.address == SAMPLE_ADDRESS
    assert user.address.city == "NYC"


def test_typed_map_model_none():
    """Typed MapAttribute defaults to None when not provided."""
    user = User(pk="USER#1")

    assert user.address is None


def test_typed_map_to_dict():
    """to_dict serializes typed map to dict (not JSON string)."""
    user = _user_with_address()

    result = user.to_dict()

    assert result["address"] == SAMPLE_ADDRESS_DICT


def test_typed_map_from_dict():
    """from_dict deserializes dict to typed model."""
    user = User.from_dict(_user_dict())

    assert user.address == SAMPLE_ADDRESS


# --- Backward compatibility ---


def test_untyped_map_still_works():
    """Untyped MapAttribute works exactly as before."""
    profile = Profile(pk="PROF#1", metadata={"theme": "dark", "lang": "en"})

    assert profile.metadata == {"theme": "dark", "lang": "en"}

    result = profile.to_dict()
    assert result["metadata"] == {"theme": "dark", "lang": "en"}


def test_untyped_map_from_dict():
    """Untyped MapAttribute from_dict returns plain dict."""
    profile = Profile.from_dict({"pk": "PROF#1", "metadata": {"theme": "dark"}})

    assert profile.metadata == {"theme": "dark"}
    assert isinstance(profile.metadata, dict)


# --- In-place mutation tracking ---


def test_map_snapshots_built_on_from_dict():
    """from_dict should build snapshots for typed MapAttributes."""
    user = User.from_dict(_user_dict())

    assert "address" in user._json_snapshots


def test_map_snapshots_empty_for_untyped():
    """Untyped MapAttribute should not produce snapshots."""
    profile = Profile.from_dict({"pk": "PROF#1", "metadata": {"theme": "dark"}})

    assert profile._json_snapshots == {}


def test_detect_inplace_map_mutation():
    """_detect_json_mutations catches in-place changes on typed MapAttribute."""
    user = User.from_dict(_user_dict())
    assert user.is_dirty is False

    user.address.city = "Brooklyn"
    user._detect_json_mutations()

    assert user.is_dirty is True
    assert "address" in user.changed_fields


def test_no_false_positive_without_map_mutation():
    """_detect_json_mutations should not flag unchanged MapAttributes."""
    user = User.from_dict(_user_dict())

    user._detect_json_mutations()

    assert user.is_dirty is False


def test_detect_map_mutation_with_none_value():
    """_detect_json_mutations handles None address correctly."""
    user = User.from_dict({"pk": "USER#1"})

    user._detect_json_mutations()

    assert user.is_dirty is False


@MemoryBackend()
def test_inplace_map_mutation_detected_on_save():
    """sync_save detects in-place mutations on typed MapAttributes."""
    user = _user_with_address()
    user.sync_save()

    loaded = User.sync_get(pk="USER#1")
    loaded.address.city = "Brooklyn"
    loaded.sync_save()

    result = User.sync_get(pk="USER#1")
    assert result.address.city == "Brooklyn"
    assert result.address.street == "123 Main St"


@MemoryBackend()
def test_reset_tracking_rebuilds_map_snapshots():
    """_reset_change_tracking should rebuild snapshots for MapAttributes."""
    user = _user_with_address()
    user.sync_save()

    assert "address" in user._json_snapshots
    assert "NYC" in user._json_snapshots["address"]

    loaded = User.sync_get(pk="USER#1")
    loaded.address.city = "Brooklyn"
    loaded.sync_save()

    assert "Brooklyn" in loaded._json_snapshots["address"]


@MemoryBackend()
def test_assignment_still_tracked_for_typed_map():
    """Full assignment (not in-place) is still tracked via __setattr__."""
    user = _user_with_address()
    user.sync_save()

    loaded = User.sync_get(pk="USER#1")
    loaded.address = Address(street="456 Elm St", city="Chicago", zip="60601")

    assert loaded.is_dirty is True
    assert "address" in loaded.changed_fields


def test_map_with_plain_class_serializes_value_as_is():
    """A model_class that is neither Pydantic nor a dataclass passes the value through."""

    class PlainAddress:
        pass

    # GIVEN a MapAttribute typed with a plain class
    attr = MapAttribute(PlainAddress)
    value = {"city": "NYC"}

    # WHEN we serialize a plain dict
    result = attr.serialize(value)

    # THEN the same value is returned unchanged
    assert result is value


@dataclasses.dataclass
class Order:
    quantity: int
    note: str | None = None
    total: int = dataclasses.field(init=False)

    def __post_init__(self) -> None:
        self.total = self.quantity * 10


class Cart(Model):
    model_config = ModelConfig(table="carts")
    pk = StringAttribute(partition_key=True)
    order = MapAttribute(Order)


@pytest.mark.parametrize("note", [None, "gift"])
def test_typed_map_round_trips_init_false_field(note):
    """deserialize leaves init=False fields to __post_init__, not the constructor."""
    attr = MapAttribute(Order)
    original = Order(quantity=3, note=note)

    restored = attr.deserialize(attr.serialize(original))

    assert restored == original
    assert restored.total == 30


def test_typed_map_recomputes_stored_init_false_field():
    """A stored value for an init=False field is ignored and rebuilt by __post_init__."""
    attr = MapAttribute(Order)

    restored = attr.deserialize({"quantity": 2, "note": None, "total": 999})

    assert restored.total == 20


def test_typed_map_round_trips_plain_dataclass():
    """A dataclass without init=False fields still round-trips."""
    attr = MapAttribute(Address)

    assert attr.deserialize(attr.serialize(SAMPLE_ADDRESS)) == SAMPLE_ADDRESS


@MemoryBackend()
def test_typed_map_init_false_field_survives_save_and_get():
    """A dataclass with an init=False field loads back after a save."""
    Cart(pk="CART#1", order=Order(quantity=4)).sync_save()

    loaded = Cart.sync_get(pk="CART#1")

    assert loaded.order == Order(quantity=4)
    assert loaded.order.total == 40
