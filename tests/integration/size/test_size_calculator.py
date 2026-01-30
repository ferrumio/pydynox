"""Integration tests for item size calculator with Model."""

import pytest
from pydynox import Model, ModelConfig
from pydynox.attributes import ListAttribute, MapAttribute, NumberAttribute, StringAttribute
from pydynox.exceptions import ItemTooLargeException


def test_calculate_size_simple_item(dynamo):
    """calculate_size returns correct size for simple item."""

    class User(Model):
        model_config = ModelConfig(table="test_table", client=dynamo)
        pk = StringAttribute(partition_key=True)
        sk = StringAttribute(sort_key=True)
        name = StringAttribute()
        age = NumberAttribute()

    User._client_instance = None

    # GIVEN a simple model instance
    user = User(pk="USER#1", sk="PROFILE", name="John", age=30)

    # WHEN we calculate size
    size = user.calculate_size()

    # THEN size info is returned
    assert size.bytes > 0
    assert size.kb > 0
    assert size.percent < 1  # Small item
    assert size.is_over_limit is False


def test_calculate_size_with_nested_data(dynamo):
    """calculate_size handles nested structures."""

    class User(Model):
        model_config = ModelConfig(table="test_table", client=dynamo)
        pk = StringAttribute(partition_key=True)
        sk = StringAttribute(sort_key=True)
        name = StringAttribute()
        tags = ListAttribute()
        metadata = MapAttribute()

    User._client_instance = None

    user = User(
        pk="USER#2",
        sk="PROFILE",
        name="Jane",
        tags=["admin", "active", "verified"],
        metadata={"role": "admin", "level": 5},
    )
    size = user.calculate_size()

    assert size.bytes > 50  # Has nested data
    assert size.is_over_limit is False


def test_calculate_size_detailed_breakdown(dynamo):
    """calculate_size with detailed=True returns field breakdown."""

    class User(Model):
        model_config = ModelConfig(table="test_table", client=dynamo)
        pk = StringAttribute(partition_key=True)
        sk = StringAttribute(sort_key=True)
        name = StringAttribute()
        bio = StringAttribute()

    User._client_instance = None

    user = User(
        pk="USER#3",
        sk="PROFILE",
        name="Bob",
        bio="A" * 1000,  # Large bio
    )
    size = user.calculate_size(detailed=True)

    assert "bio" in size.fields
    assert size.fields["bio"] > 1000  # bio field is largest
    assert size.fields["pk"] < size.fields["bio"]


@pytest.mark.asyncio
async def test_save_succeeds_under_limit(dynamo):
    """save() works when item is under max_size."""

    class LimitedUser(Model):
        model_config = ModelConfig(table="test_table", client=dynamo, max_size=500)
        pk = StringAttribute(partition_key=True)
        sk = StringAttribute(sort_key=True)
        bio = StringAttribute()

    LimitedUser._client_instance = None

    user = LimitedUser(pk="USER#4", sk="PROFILE", bio="Short bio")
    await user.save()

    # Verify it was saved
    result = await dynamo.get_item("test_table", {"pk": "USER#4", "sk": "PROFILE"})
    assert result["bio"] == "Short bio"


@pytest.mark.asyncio
async def test_save_raises_when_over_limit(dynamo):
    """save() raises ItemTooLargeException when item exceeds max_size."""

    class LimitedUser(Model):
        model_config = ModelConfig(table="test_table", client=dynamo, max_size=500)
        pk = StringAttribute(partition_key=True)
        sk = StringAttribute(sort_key=True)
        bio = StringAttribute()

    LimitedUser._client_instance = None

    # GIVEN a model with data exceeding max_size
    user = LimitedUser(
        pk="USER#5",
        sk="PROFILE",
        bio="X" * 1000,  # Way over 500 byte limit
    )

    # WHEN we try to save
    # THEN ItemTooLargeException is raised
    with pytest.raises(ItemTooLargeException) as exc_info:
        await user.save()

    assert exc_info.value.size > 500
    assert exc_info.value.max_size == 500
    assert exc_info.value.item_key == {"pk": "USER#5", "sk": "PROFILE"}


@pytest.mark.asyncio
async def test_save_without_limit_allows_large_items(dynamo):
    """save() without max_size allows large items."""

    class User(Model):
        model_config = ModelConfig(table="test_table", client=dynamo)
        pk = StringAttribute(partition_key=True)
        sk = StringAttribute(sort_key=True)
        bio = StringAttribute()

    User._client_instance = None

    user = User(
        pk="USER#6",
        sk="PROFILE",
        bio="Y" * 10000,  # Large but under 400KB
    )
    await user.save()

    result = await dynamo.get_item("test_table", {"pk": "USER#6", "sk": "PROFILE"})
    assert len(result["bio"]) == 10000
