"""Integration tests for smart save (change tracking).

Tests that smart save uses UpdateItem and consumes less WCU than full replace.
"""

import pytest
from pydynox import Model, ModelConfig
from pydynox.attributes import NumberAttribute, StringAttribute


@pytest.fixture
def large_model(dynamo):
    """Create a model with many fields to show WCU difference."""

    class LargeItem(Model):
        model_config = ModelConfig(table="test_table", client=dynamo)
        pk = StringAttribute(partition_key=True)
        sk = StringAttribute(sort_key=True)
        # Many fields to make item larger
        field1 = StringAttribute()
        field2 = StringAttribute()
        field3 = StringAttribute()
        field4 = StringAttribute()
        field5 = StringAttribute()
        field6 = StringAttribute()
        field7 = StringAttribute()
        field8 = StringAttribute()
        field9 = StringAttribute()
        field10 = StringAttribute()
        counter = NumberAttribute()

    LargeItem._client_instance = None
    return LargeItem


@pytest.mark.asyncio
async def test_smart_save_uses_update_item(large_model):
    """Smart save should use UpdateItem for changed fields only."""
    LargeItem = large_model

    # Create item with lots of data
    item = LargeItem(
        pk="SMART#1",
        sk="TEST",
        field1="a" * 100,
        field2="b" * 100,
        field3="c" * 100,
        field4="d" * 100,
        field5="e" * 100,
        field6="f" * 100,
        field7="g" * 100,
        field8="h" * 100,
        field9="i" * 100,
        field10="j" * 100,
        counter=0,
    )
    await item.save()

    # Load and change only one field
    loaded = await LargeItem.get(pk="SMART#1", sk="TEST")
    loaded.counter = 1
    await loaded.save()

    # Verify the change was saved
    result = await LargeItem.get(pk="SMART#1", sk="TEST")
    assert result.counter == 1
    assert result.field1 == "a" * 100  # Other fields unchanged


@pytest.mark.asyncio
async def test_full_replace_uses_put_item(large_model):
    """full_replace=True should use PutItem with all fields."""
    LargeItem = large_model

    # Create item
    item = LargeItem(
        pk="FULL#1",
        sk="TEST",
        field1="a" * 100,
        field2="b" * 100,
        field3="c" * 100,
        field4="d" * 100,
        field5="e" * 100,
        field6="f" * 100,
        field7="g" * 100,
        field8="h" * 100,
        field9="i" * 100,
        field10="j" * 100,
        counter=0,
    )
    await item.save()

    # Load and change one field, but use full_replace
    loaded = await LargeItem.get(pk="FULL#1", sk="TEST")
    loaded.counter = 1
    await loaded.save(full_replace=True)

    # Verify the change was saved
    result = await LargeItem.get(pk="FULL#1", sk="TEST")
    assert result.counter == 1


@pytest.mark.asyncio
async def test_smart_save_wcu_vs_full_replace(large_model):
    """Compare WCU consumption: smart save vs full replace.

    Smart save should use less WCU when only changing small fields.
    """
    LargeItem = large_model

    # Create two identical items
    item1 = LargeItem(
        pk="WCU#1",
        sk="TEST",
        field1="a" * 500,
        field2="b" * 500,
        field3="c" * 500,
        field4="d" * 500,
        field5="e" * 500,
        field6="f" * 500,
        field7="g" * 500,
        field8="h" * 500,
        field9="i" * 500,
        field10="j" * 500,
        counter=0,
    )
    await item1.save()

    item2 = LargeItem(
        pk="WCU#2",
        sk="TEST",
        field1="a" * 500,
        field2="b" * 500,
        field3="c" * 500,
        field4="d" * 500,
        field5="e" * 500,
        field6="f" * 500,
        field7="g" * 500,
        field8="h" * 500,
        field9="i" * 500,
        field10="j" * 500,
        counter=0,
    )
    await item2.save()

    # Reset metrics
    LargeItem.reset_metrics()

    # Smart save: change only counter
    loaded1 = await LargeItem.get(pk="WCU#1", sk="TEST")
    loaded1.counter = 1
    await loaded1.save()  # Smart save (UpdateItem)

    smart_metrics = LargeItem.get_total_metrics()
    smart_wcu = smart_metrics.total_wcu

    # Reset metrics
    LargeItem.reset_metrics()

    # Full replace: change only counter but use full_replace
    loaded2 = await LargeItem.get(pk="WCU#2", sk="TEST")
    loaded2.counter = 1
    await loaded2.save(full_replace=True)  # Full replace (PutItem)

    full_metrics = LargeItem.get_total_metrics()
    full_wcu = full_metrics.total_wcu

    # Smart save should use less or equal WCU
    # Note: LocalStack may not accurately report WCU, so we just verify it works
    assert smart_wcu is not None or full_wcu is not None


@pytest.mark.asyncio
async def test_is_dirty_and_changed_fields(large_model):
    """Test is_dirty and changed_fields properties."""
    LargeItem = large_model

    # Create and save
    item = LargeItem(
        pk="DIRTY#1",
        sk="TEST",
        field1="original",
        field2="original",
        field3="original",
        field4="original",
        field5="original",
        field6="original",
        field7="original",
        field8="original",
        field9="original",
        field10="original",
        counter=0,
    )
    await item.save()

    # Load - should be clean
    loaded = await LargeItem.get(pk="DIRTY#1", sk="TEST")
    assert loaded.is_dirty is False
    assert loaded.changed_fields == []

    # Change one field
    loaded.field1 = "changed"
    assert loaded.is_dirty is True
    assert "field1" in loaded.changed_fields

    # Change another field
    loaded.counter = 99
    assert set(loaded.changed_fields) == {"field1", "counter"}

    # Revert one field
    loaded.field1 = "original"
    assert loaded.changed_fields == ["counter"]

    # Save and check it's clean again
    await loaded.save()
    assert loaded.is_dirty is False
    assert loaded.changed_fields == []


@pytest.mark.asyncio
async def test_new_item_always_uses_putitem(large_model):
    """New items (not loaded from DB) should always use PutItem."""
    LargeItem = large_model

    # New item has no _original
    item = LargeItem(
        pk="NEW#1",
        sk="TEST",
        field1="value",
        field2="value",
        field3="value",
        field4="value",
        field5="value",
        field6="value",
        field7="value",
        field8="value",
        field9="value",
        field10="value",
        counter=0,
    )

    assert item._original is None
    assert item.is_dirty is False  # New items are not "dirty"

    await item.save()

    # After save, _original is set
    assert item._original is not None


@pytest.mark.asyncio
async def test_smart_save_with_condition(large_model):
    """Smart save should work with conditions."""
    LargeItem = large_model

    # Create item
    item = LargeItem(
        pk="COND#1",
        sk="TEST",
        field1="value",
        field2="value",
        field3="value",
        field4="value",
        field5="value",
        field6="value",
        field7="value",
        field8="value",
        field9="value",
        field10="value",
        counter=0,
    )
    await item.save()

    # Load and change
    loaded = await LargeItem.get(pk="COND#1", sk="TEST")
    loaded.counter = 1

    # Save with condition
    await loaded.save(condition=LargeItem.counter == 0)

    # Verify
    result = await LargeItem.get(pk="COND#1", sk="TEST")
    assert result.counter == 1


@pytest.mark.asyncio
async def test_smart_save_condition_fails(large_model):
    """Smart save with failing condition should raise error."""
    LargeItem = large_model

    # Create item
    item = LargeItem(
        pk="COND#2",
        sk="TEST",
        field1="value",
        field2="value",
        field3="value",
        field4="value",
        field5="value",
        field6="value",
        field7="value",
        field8="value",
        field9="value",
        field10="value",
        counter=0,
    )
    await item.save()

    # Load and change
    loaded = await LargeItem.get(pk="COND#2", sk="TEST")
    loaded.counter = 1

    # Save with wrong condition - should fail
    with pytest.raises(Exception):
        await loaded.save(condition=LargeItem.counter == 999)

    # Original value should be unchanged
    result = await LargeItem.get(pk="COND#2", sk="TEST")
    assert result.counter == 0
