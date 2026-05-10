"""Integration tests for update/update_by_key serialization of typed attributes.

Regression tests for https://github.com/ferrumio/pydynox/issues/377
"""

import dataclasses
import uuid

from pydynox import Model, ModelConfig
from pydynox.attributes import MapAttribute, StringAttribute


@dataclasses.dataclass
class Address:
    street: str
    city: str
    zip: str


def _make_user_model(dynamo):
    table = "test_table"

    class User(Model):
        model_config = ModelConfig(table=table, client=dynamo)
        pk = StringAttribute(partition_key=True)
        sk = StringAttribute(sort_key=True)
        address = MapAttribute(Address)

    return User


def test_sync_update_serializes_typed_map(dynamo):
    """sync_update correctly serializes a typed MapAttribute (dataclass)."""
    User = _make_user_model(dynamo)
    pk = f"UPD_SER#{uuid.uuid4().hex[:8]}"

    # GIVEN a saved user with an address
    user = User(
        pk=pk,
        sk="PROFILE",
        address=Address(street="123 Main St", city="NYC", zip="10001"),
    )
    user.sync_save()

    # WHEN updating the address via sync_update
    new_address = Address(street="456 Elm St", city="Chicago", zip="60601")
    user.sync_update(address=new_address)

    # THEN the new address is persisted and deserialized correctly
    retrieved = User.sync_get(pk=pk, sk="PROFILE")
    assert retrieved.address == new_address
    assert retrieved.address.city == "Chicago"
    assert retrieved.address.street == "456 Elm St"


def test_sync_update_by_key_serializes_typed_map(dynamo):
    """sync_update_by_key correctly serializes a typed MapAttribute (dataclass)."""
    User = _make_user_model(dynamo)
    pk = f"UBK_SER#{uuid.uuid4().hex[:8]}"

    # GIVEN a saved user with an address
    user = User(
        pk=pk,
        sk="PROFILE",
        address=Address(street="123 Main St", city="NYC", zip="10001"),
    )
    user.sync_save()

    # WHEN updating via update_by_key
    new_address = Address(street="789 Pine St", city="Seattle", zip="98101")
    User.sync_update_by_key(pk=pk, sk="PROFILE", address=new_address)

    # THEN the new address is persisted and deserialized correctly
    retrieved = User.sync_get(pk=pk, sk="PROFILE")
    assert retrieved.address == new_address
    assert retrieved.address.city == "Seattle"
    assert retrieved.address.zip == "98101"


def test_sync_update_serializes_none_typed_map(dynamo):
    """sync_update correctly handles setting a typed MapAttribute to None."""
    User = _make_user_model(dynamo)
    pk = f"UPD_NONE#{uuid.uuid4().hex[:8]}"

    # GIVEN a saved user with an address
    user = User(
        pk=pk,
        sk="PROFILE",
        address=Address(street="123 Main St", city="NYC", zip="10001"),
    )
    user.sync_save()

    # WHEN setting address to None
    user.sync_update(address=None)

    # THEN address is None
    retrieved = User.sync_get(pk=pk, sk="PROFILE")
    assert retrieved.address is None
