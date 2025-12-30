"""Integration tests for item size calculator with Model."""

import pytest
from pydynox import Model
from pydynox.attributes import ListAttribute, MapAttribute, NumberAttribute, StringAttribute
from pydynox.exceptions import ItemTooLargeError

from ..conftest import MOTO_ENDPOINT


class User(Model):
    """Test model without size limit."""

    class Meta:
        table = "test_table"
        region = "us-east-1"
        endpoint_url = MOTO_ENDPOINT

    pk = StringAttribute(hash_key=True)
    sk = StringAttribute(range_key=True)
    name = StringAttribute(null=True)
    age = NumberAttribute(null=True)
    bio = StringAttribute(null=True)
    tags = ListAttribute(null=True)
    metadata = MapAttribute(null=True)


class LimitedUser(Model):
    """Test model with size limit."""

    class Meta:
        table = "test_table"
        region = "us-east-1"
        endpoint_url = MOTO_ENDPOINT
        max_size = 500  # 500 bytes limit

    pk = StringAttribute(hash_key=True)
    sk = StringAttribute(range_key=True)
    bio = StringAttribute(null=True)


def test_calculate_size_simple_item(moto_server):
    """calculate_size returns correct size for simple item."""
    user = User(pk="USER#1", sk="PROFILE", name="John", age=30)
    size = user.calculate_size()

    assert size.bytes > 0
    assert size.kb > 0
    assert size.percent < 1  # Small item
    assert size.is_over_limit is False


def test_calculate_size_with_nested_data(moto_server):
    """calculate_size handles nested structures."""
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


def test_calculate_size_detailed_breakdown(moto_server):
    """calculate_size with detailed=True returns field breakdown."""
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


def test_save_succeeds_under_limit(dynamo, table):
    """save() works when item is under max_size."""
    user = LimitedUser(pk="USER#4", sk="PROFILE", bio="Short bio")
    user.save()

    # Verify it was saved
    result = dynamo.get_item("test_table", {"pk": "USER#4", "sk": "PROFILE"})
    assert result["bio"] == "Short bio"


def test_save_raises_when_over_limit(moto_server):
    """save() raises ItemTooLargeError when item exceeds max_size."""
    user = LimitedUser(
        pk="USER#5",
        sk="PROFILE",
        bio="X" * 1000,  # Way over 500 byte limit
    )

    with pytest.raises(ItemTooLargeError) as exc_info:
        user.save()

    assert exc_info.value.size > 500
    assert exc_info.value.max_size == 500
    assert exc_info.value.item_key == {"pk": "USER#5", "sk": "PROFILE"}


def test_save_without_limit_allows_large_items(dynamo, table):
    """save() without max_size allows large items."""
    user = User(
        pk="USER#6",
        sk="PROFILE",
        bio="Y" * 10000,  # Large but under 400KB
    )
    user.save()

    result = dynamo.get_item("test_table", {"pk": "USER#6", "sk": "PROFILE"})
    assert len(result["bio"]) == 10000
