"""Async integration tests for JSONAttribute with RootModel and arbitrary types.

Regression tests for https://github.com/ferrumio/pydynox/issues/367
"""

import uuid

import pytest
from pydantic import BaseModel, RootModel
from pydynox import Model, ModelConfig
from pydynox.attributes import JSONAttribute, StringAttribute


class Item(BaseModel):
    name: str
    qty: int


class ItemList(RootModel[list[Item]]):
    pass


class TagList(RootModel[list[str]]):
    pass


class Inventory(Model):
    model_config = ModelConfig(table="test_table")
    pk = StringAttribute(partition_key=True)
    sk = StringAttribute(sort_key=True)
    items = JSONAttribute(ItemList)


class TagModel(Model):
    model_config = ModelConfig(table="test_table")
    pk = StringAttribute(partition_key=True)
    sk = StringAttribute(sort_key=True)
    tags = JSONAttribute(TagList)


class ScoreModel(Model):
    model_config = ModelConfig(table="test_table")
    pk = StringAttribute(partition_key=True)
    sk = StringAttribute(sort_key=True)
    scores = JSONAttribute(list[str])


@pytest.mark.asyncio
async def test_rootmodel_list_save_and_get(dynamo):
    """RootModel[list[...]] round-trips through save/get."""
    pk = f"RM_ASYNC#{uuid.uuid4().hex[:8]}"
    Inventory.model_config = ModelConfig(table="test_table", client=dynamo)

    # GIVEN items as a RootModel list
    items = ItemList([Item(name="widget", qty=5), Item(name="gadget", qty=3)])
    inv = Inventory(pk=pk, sk="INV", items=items)

    # WHEN saving and retrieving
    await inv.save()
    retrieved = await Inventory.get(pk=pk, sk="INV")

    # THEN the RootModel is reconstructed
    assert isinstance(retrieved.items, ItemList)
    assert len(retrieved.items.root) == 2
    assert retrieved.items.root[0].name == "widget"
    assert retrieved.items.root[1].qty == 3


@pytest.mark.asyncio
async def test_rootmodel_list_update(dynamo):
    """RootModel[list[...]] works with async update."""
    pk = f"RM_UPD_ASYNC#{uuid.uuid4().hex[:8]}"
    Inventory.model_config = ModelConfig(table="test_table", client=dynamo)

    # GIVEN a saved inventory
    items = ItemList([Item(name="widget", qty=5)])
    inv = Inventory(pk=pk, sk="INV", items=items)
    await inv.save()

    # WHEN updating with a new list
    new_items = ItemList([Item(name="gizmo", qty=10)])
    await inv.update(items=new_items)

    # THEN the update is persisted
    retrieved = await Inventory.get(pk=pk, sk="INV")
    assert retrieved.items.root[0].name == "gizmo"
    assert retrieved.items.root[0].qty == 10


@pytest.mark.asyncio
async def test_rootmodel_strings_save_and_get(dynamo):
    """RootModel[list[str]] round-trips correctly."""
    pk = f"RM_STR_ASYNC#{uuid.uuid4().hex[:8]}"
    TagModel.model_config = ModelConfig(table="test_table", client=dynamo)

    tags = TagList(["python", "rust", "dynamodb"])
    model = TagModel(pk=pk, sk="TAGS", tags=tags)
    await model.save()

    retrieved = await TagModel.get(pk=pk, sk="TAGS")
    assert isinstance(retrieved.tags, TagList)
    assert retrieved.tags.root == ["python", "rust", "dynamodb"]


@pytest.mark.asyncio
async def test_arbitrary_type_save_and_get(dynamo):
    """JSONAttribute(list[str]) works with arbitrary types via TypeAdapter."""
    pk = f"ARB_ASYNC#{uuid.uuid4().hex[:8]}"
    ScoreModel.model_config = ModelConfig(table="test_table", client=dynamo)

    model = ScoreModel(pk=pk, sk="SCORES", scores=["high", "medium", "low"])
    await model.save()

    retrieved = await ScoreModel.get(pk=pk, sk="SCORES")
    assert retrieved.scores == ["high", "medium", "low"]
