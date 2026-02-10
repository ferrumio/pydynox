"""Tests for field alias feature.

Aliases let you use readable Python names while storing short names in DynamoDB.
"""

from __future__ import annotations

import pytest
from pydynox.attributes import NumberAttribute, StringAttribute
from pydynox.config import ModelConfig
from pydynox.model import Model
from pydynox.testing import MemoryBackend

# ── Test models ──────────────────────────────────────────────────────────────


class UserWithAlias(Model):
    model_config = ModelConfig(table="users")

    pk = StringAttribute(partition_key=True)
    sk = StringAttribute(sort_key=True)
    email = StringAttribute(alias="em")
    first_name = StringAttribute(alias="fn")
    age = NumberAttribute(alias="a")


class NoAliasModel(Model):
    model_config = ModelConfig(table="items")

    pk = StringAttribute(partition_key=True)
    name = StringAttribute()


class KeyAliasModel(Model):
    """Model where even the keys have aliases."""

    model_config = ModelConfig(table="things")

    pk = StringAttribute(partition_key=True, alias="p")
    sk = StringAttribute(sort_key=True, alias="s")
    data = StringAttribute(alias="d")


# ── to_dict / from_dict ─────────────────────────────────────────────────────


def test_to_dict_uses_alias():
    user = UserWithAlias(
        pk="USER#1", sk="PROFILE", email="john@test.com", first_name="John", age=30
    )
    d = user.to_dict()

    assert d["pk"] == "USER#1"
    assert d["sk"] == "PROFILE"
    assert d["em"] == "john@test.com"
    assert d["fn"] == "John"
    assert d["a"] == 30
    # Python names should NOT appear in the dict
    assert "email" not in d
    assert "first_name" not in d
    assert "age" not in d


def test_from_dict_translates_alias_back():
    data = {"pk": "USER#1", "sk": "PROFILE", "em": "john@test.com", "fn": "John", "a": 30}
    user = UserWithAlias.from_dict(data)

    assert user.pk == "USER#1"
    assert user.sk == "PROFILE"
    assert user.email == "john@test.com"
    assert user.first_name == "John"
    assert user.age == 30


def test_no_alias_model_uses_python_names():
    item = NoAliasModel(pk="ITEM#1", name="Test")
    d = item.to_dict()

    assert d["pk"] == "ITEM#1"
    assert d["name"] == "Test"


def test_key_alias_in_to_dict():
    item = KeyAliasModel(pk="PK#1", sk="SK#1", data="hello")
    d = item.to_dict()

    assert d["p"] == "PK#1"
    assert d["s"] == "SK#1"
    assert d["d"] == "hello"
    assert "pk" not in d
    assert "sk" not in d


def test_key_alias_from_dict():
    data = {"p": "PK#1", "s": "SK#1", "d": "hello"}
    item = KeyAliasModel.from_dict(data)

    assert item.pk == "PK#1"
    assert item.sk == "SK#1"
    assert item.data == "hello"


# ── _get_key ─────────────────────────────────────────────────────────────────


def test_get_key_uses_alias():
    item = KeyAliasModel(pk="PK#1", sk="SK#1", data="hello")
    key = item._get_key()

    assert key == {"p": "PK#1", "s": "SK#1"}


def test_get_key_no_alias():
    user = NoAliasModel(pk="ITEM#1", name="Test")
    key = user._get_key()

    assert key == {"pk": "ITEM#1"}


# ── _extract_key_from_kwargs ────────────────────────────────────────────────


def test_extract_key_uses_alias():
    key, updates = KeyAliasModel._extract_key_from_kwargs(
        {"pk": "PK#1", "sk": "SK#1", "data": "hello"}
    )

    assert key == {"p": "PK#1", "s": "SK#1"}
    assert updates == {"data": "hello"}


# ── _py_to_dynamo / _dynamo_to_py dicts ─────────────────────────────────────


def test_py_to_dynamo_mapping():
    assert UserWithAlias._py_to_dynamo == {
        "email": "em",
        "first_name": "fn",
        "age": "a",
    }


def test_dynamo_to_py_mapping():
    assert UserWithAlias._dynamo_to_py == {
        "em": "email",
        "fn": "first_name",
        "a": "age",
    }


def test_no_alias_empty_mappings():
    assert NoAliasModel._py_to_dynamo == {}
    assert NoAliasModel._dynamo_to_py == {}


# ── Conditions use alias ────────────────────────────────────────────────────


def test_condition_uses_alias():
    cond = UserWithAlias.email == "test@test.com"
    names: dict[str, str] = {}
    values: dict[str, object] = {}
    cond.serialize(names, values)

    # The path should use "em" (alias), not "email"
    assert "em" in names
    assert "email" not in names
    assert ":v0" in values
    assert values[":v0"] == "test@test.com"


def test_condition_no_alias_uses_python_name():
    cond = NoAliasModel.name == "Test"
    names: dict[str, str] = {}
    values: dict[str, object] = {}
    cond.serialize(names, values)

    assert "name" in names


def test_condition_exists_uses_alias():
    cond = UserWithAlias.email.exists()
    names: dict[str, str] = {}
    values: dict[str, object] = {}
    expr = cond.serialize(names, values)

    assert "em" in names
    assert "attribute_exists" in expr


def test_condition_begins_with_uses_alias():
    cond = UserWithAlias.first_name.begins_with("Jo")
    names: dict[str, str] = {}
    values: dict[str, object] = {}
    expr = cond.serialize(names, values)

    assert "fn" in names
    assert "begins_with" in expr


# ── Atomic updates use alias ────────────────────────────────────────────────


def test_atomic_set_uses_alias():
    op = UserWithAlias.age.set(25)
    names: dict[str, str] = {}
    values: dict[str, object] = {}
    op.serialize(names, values)

    assert "a" in names
    assert "age" not in names


def test_atomic_add_uses_alias():
    op = UserWithAlias.age.add(1)
    names: dict[str, str] = {}
    values: dict[str, object] = {}
    op.serialize(names, values)

    assert "a" in names


def test_atomic_remove_uses_alias():
    op = UserWithAlias.email.remove()
    names: dict[str, str] = {}
    values: dict[str, object] = {}
    op.serialize(names, values)

    assert "em" in names


# ── Memory backend roundtrip ────────────────────────────────────────────────


@MemoryBackend()
def test_save_and_get_with_alias():
    user = UserWithAlias(
        pk="USER#1", sk="PROFILE", email="john@test.com", first_name="John", age=30
    )
    user.sync_save()

    loaded = UserWithAlias.sync_get(pk="USER#1", sk="PROFILE")
    assert loaded is not None
    assert loaded.email == "john@test.com"
    assert loaded.first_name == "John"
    assert loaded.age == 30


@MemoryBackend()
def test_save_stores_alias_keys_in_backend():
    """Verify the in-memory backend stores aliased keys."""
    user = UserWithAlias(
        pk="USER#1", sk="PROFILE", email="john@test.com", first_name="John", age=30
    )
    user.sync_save()

    # The item stored in memory should use alias names
    stored = user.to_dict()
    assert "em" in stored
    assert "fn" in stored
    assert "a" in stored


@MemoryBackend()
def test_update_with_alias():
    user = UserWithAlias(pk="USER#1", sk="PROFILE", email="old@test.com", first_name="John", age=25)
    user.sync_save()

    user.sync_update(age=26)

    loaded = UserWithAlias.sync_get(pk="USER#1", sk="PROFILE")
    assert loaded is not None
    assert loaded.age == 26


@MemoryBackend()
def test_delete_with_alias():
    user = UserWithAlias(
        pk="USER#1", sk="PROFILE", email="john@test.com", first_name="John", age=30
    )
    user.sync_save()

    user.sync_delete()

    loaded = UserWithAlias.sync_get(pk="USER#1", sk="PROFILE")
    assert loaded is None


@MemoryBackend()
def test_key_alias_save_and_get():
    item = KeyAliasModel(pk="PK#1", sk="SK#1", data="hello")
    item.sync_save()

    loaded = KeyAliasModel.sync_get(pk="PK#1", sk="SK#1")
    assert loaded is not None
    assert loaded.data == "hello"


# ── Change tracking with alias ──────────────────────────────────────────────


@MemoryBackend()
def test_change_tracking_uses_python_names():
    """Change tracking should use Python names, not aliases."""
    user = UserWithAlias(pk="USER#1", sk="PROFILE", email="old@test.com", first_name="John", age=25)
    user.sync_save()

    loaded = UserWithAlias.sync_get(pk="USER#1", sk="PROFILE")
    assert loaded is not None
    assert not loaded.is_dirty

    loaded.email = "new@test.com"
    assert loaded.is_dirty
    assert "email" in loaded.changed_fields


# ── repr uses alias keys ────────────────────────────────────────────────────


def test_repr_uses_alias_keys():
    user = UserWithAlias(
        pk="USER#1", sk="PROFILE", email="john@test.com", first_name="John", age=30
    )
    r = repr(user)

    assert "UserWithAlias(" in r
    # repr uses to_dict which uses aliases
    assert "em=" in r
    assert "fn=" in r


# ── Mixed: some fields with alias, some without ─────────────────────────────


def test_mixed_alias_and_no_alias():
    """pk and sk have no alias, email/first_name/age do."""
    user = UserWithAlias(
        pk="USER#1", sk="PROFILE", email="test@test.com", first_name="Jane", age=28
    )
    d = user.to_dict()

    # No alias fields keep python name
    assert "pk" in d
    assert "sk" in d
    # Alias fields use alias
    assert "em" in d
    assert "fn" in d
    assert "a" in d


# ── Equality uses aliased keys ──────────────────────────────────────────────


def test_equality_with_key_alias():
    a = KeyAliasModel(pk="PK#1", sk="SK#1", data="hello")
    b = KeyAliasModel(pk="PK#1", sk="SK#1", data="world")

    assert a == b  # Same key, different data


def test_inequality_with_key_alias():
    a = KeyAliasModel(pk="PK#1", sk="SK#1", data="hello")
    b = KeyAliasModel(pk="PK#2", sk="SK#1", data="hello")

    assert a != b


# ── Alias param on attribute ────────────────────────────────────────────────


def test_alias_param_stored_on_attribute():
    assert UserWithAlias.email.alias == "em"
    assert UserWithAlias.first_name.alias == "fn"
    assert UserWithAlias.age.alias == "a"
    assert UserWithAlias.pk.alias is None


@pytest.mark.parametrize(
    "field_name,expected_alias",
    [
        pytest.param("email", "em", id="email"),
        pytest.param("first_name", "fn", id="first_name"),
        pytest.param("age", "a", id="age"),
        pytest.param("pk", None, id="pk_no_alias"),
        pytest.param("sk", None, id="sk_no_alias"),
    ],
)
def test_alias_values(field_name, expected_alias):
    attr = UserWithAlias._attributes[field_name]
    assert attr.alias == expected_alias
