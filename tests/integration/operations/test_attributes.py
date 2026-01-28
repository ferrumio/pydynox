"""Integration tests for new attribute types."""

from datetime import datetime, timezone
from enum import Enum

import pytest
from pydynox import Model, ModelConfig
from pydynox.attributes import (
    DatetimeAttribute,
    EnumAttribute,
    JSONAttribute,
    NumberSetAttribute,
    StringAttribute,
    StringSetAttribute,
)
from pydynox.config import set_default_client


class Status(Enum):
    PENDING = "pending"
    ACTIVE = "active"


@pytest.fixture
def setup_client(dynamo):
    """Set up default client for Model operations."""
    set_default_client(dynamo)
    yield dynamo


@pytest.mark.asyncio
async def test_json_attribute_roundtrip(setup_client, table):
    """JSONAttribute saves and loads dict correctly."""

    class Config(Model):
        model_config = ModelConfig(table="test_table")
        pk = StringAttribute(hash_key=True)
        sk = StringAttribute(range_key=True)
        settings = JSONAttribute()

    # GIVEN a model with JSON data
    config = Config(
        pk="CFG#1",
        sk="SETTINGS",
        settings={"theme": "dark", "notifications": True, "count": 42},
    )

    # WHEN we save and load it
    await config.save()
    loaded = await Config.get(pk="CFG#1", sk="SETTINGS")

    # THEN JSON data is preserved
    assert loaded is not None
    assert loaded.settings == {"theme": "dark", "notifications": True, "count": 42}


@pytest.mark.asyncio
async def test_json_attribute_with_list(setup_client, table):
    """JSONAttribute saves and loads list correctly."""

    class Config(Model):
        model_config = ModelConfig(table="test_table")
        pk = StringAttribute(hash_key=True)
        sk = StringAttribute(range_key=True)
        items = JSONAttribute()

    config = Config(pk="CFG#2", sk="ITEMS", items=["a", "b", "c"])
    await config.save()

    loaded = await Config.get(pk="CFG#2", sk="ITEMS")
    assert loaded is not None
    assert loaded.items == ["a", "b", "c"]


@pytest.mark.asyncio
async def test_enum_attribute_roundtrip(setup_client, table):
    """EnumAttribute saves and loads enum correctly."""

    class User(Model):
        model_config = ModelConfig(table="test_table")
        pk = StringAttribute(hash_key=True)
        sk = StringAttribute(range_key=True)
        status = EnumAttribute(Status)

    # GIVEN a model with enum value
    user = User(pk="USER#1", sk="PROFILE", status=Status.ACTIVE)

    # WHEN we save and load it
    await user.save()
    loaded = await User.get(pk="USER#1", sk="PROFILE")

    # THEN enum value is preserved
    assert loaded is not None
    assert loaded.status == Status.ACTIVE


@pytest.mark.asyncio
async def test_enum_attribute_with_default(setup_client, table):
    """EnumAttribute uses default value."""

    class User(Model):
        model_config = ModelConfig(table="test_table")
        pk = StringAttribute(hash_key=True)
        sk = StringAttribute(range_key=True)
        status = EnumAttribute(Status, default=Status.PENDING)

    user = User(pk="USER#2", sk="PROFILE")
    await user.save()

    loaded = await User.get(pk="USER#2", sk="PROFILE")
    assert loaded is not None
    assert loaded.status == Status.PENDING


@pytest.mark.asyncio
async def test_datetime_attribute_roundtrip(setup_client, table):
    """DatetimeAttribute saves and loads datetime correctly."""

    class Event(Model):
        model_config = ModelConfig(table="test_table")
        pk = StringAttribute(hash_key=True)
        sk = StringAttribute(range_key=True)
        created_at = DatetimeAttribute()

    # GIVEN a model with datetime value
    dt = datetime(2024, 6, 15, 10, 30, 0, tzinfo=timezone.utc)
    event = Event(pk="EVT#1", sk="DATA", created_at=dt)

    # WHEN we save and load it
    await event.save()
    loaded = await Event.get(pk="EVT#1", sk="DATA")

    # THEN datetime is preserved
    assert loaded is not None
    assert loaded.created_at == dt


@pytest.mark.asyncio
async def test_string_set_attribute_roundtrip(setup_client, table):
    """StringSetAttribute saves and loads set correctly."""

    class User(Model):
        model_config = ModelConfig(table="test_table")
        pk = StringAttribute(hash_key=True)
        sk = StringAttribute(range_key=True)
        tags = StringSetAttribute()

    # GIVEN a model with string set
    user = User(pk="USER#3", sk="PROFILE", tags={"admin", "verified", "premium"})

    # WHEN we save and load it
    await user.save()
    loaded = await User.get(pk="USER#3", sk="PROFILE")

    # THEN set is preserved
    assert loaded is not None
    assert loaded.tags == {"admin", "verified", "premium"}


@pytest.mark.asyncio
async def test_number_set_attribute_roundtrip(setup_client, table):
    """NumberSetAttribute saves and loads set correctly."""

    class User(Model):
        model_config = ModelConfig(table="test_table")
        pk = StringAttribute(hash_key=True)
        sk = StringAttribute(range_key=True)
        scores = NumberSetAttribute()

    user = User(pk="USER#4", sk="PROFILE", scores={100, 95, 88})
    await user.save()

    loaded = await User.get(pk="USER#4", sk="PROFILE")
    assert loaded is not None
    assert loaded.scores == {100, 95, 88}


@pytest.mark.asyncio
async def test_number_set_attribute_with_floats(setup_client, table):
    """NumberSetAttribute handles floats correctly."""

    class User(Model):
        model_config = ModelConfig(table="test_table")
        pk = StringAttribute(hash_key=True)
        sk = StringAttribute(range_key=True)
        ratings = NumberSetAttribute()

    user = User(pk="USER#5", sk="PROFILE", ratings={4.5, 3.8, 5.0})
    await user.save()

    loaded = await User.get(pk="USER#5", sk="PROFILE")
    assert loaded is not None
    # 5.0 becomes 5 (int)
    assert 4.5 in loaded.ratings
    assert 3.8 in loaded.ratings
    assert 5 in loaded.ratings or 5.0 in loaded.ratings
