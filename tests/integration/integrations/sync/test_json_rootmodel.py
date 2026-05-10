"""Integration tests for JSONAttribute with RootModel and arbitrary types.

Regression tests for https://github.com/ferrumio/pydynox/issues/367
"""

import uuid

from pydantic import BaseModel, RootModel

from pydynox import Model, ModelConfig
from pydynox.attributes import JSONAttribute, StringAttribute
from pydynox.testing import MemoryBackend


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


def test_rootmodel_list_save_and_get(dynamo):
    """RootModel[list[...]] round-trips through save/get."""
    pk = f"RM#{uuid.uuid4().hex[:8]}"
    Inventory.model_config = ModelConfig(table="test_table", client=dynamo)

    # GIVEN items as a RootModel list
    items = ItemList([Item(name="widget", qty=5), Item(name="gadget", qty=3)])
    inv = Inventory(pk=pk, sk="INV", items=items)

    # WHEN saving and retrieving
    inv.sync_save()
    retrieved = Inventory.sync_get(pk=pk, sk="INV")

    # THEN the RootModel is reconstructed
    assert isinstance(retrieved.items, ItemList)
    assert len(retrieved.items.root) == 2
    assert retrieved.items.root[0].name == "widget"
    assert retrieved.items.root[1].qty == 3


def test_rootmodel_list_update(dynamo):
    """RootModel[list[...]] works with sync_update."""
    pk = f"RM_UPD#{uuid.uuid4().hex[:8]}"
    Inventory.model_config = ModelConfig(table="test_table", client=dynamo)

    # GIVEN a saved inventory
    items = ItemList([Item(name="widget", qty=5)])
    inv = Inventory(pk=pk, sk="INV", items=items)
    inv.sync_save()

    # WHEN updating with a new list
    new_items = ItemList([Item(name="gizmo", qty=10)])
    inv.sync_update(items=new_items)

    # THEN the update is persisted
    retrieved = Inventory.sync_get(pk=pk, sk="INV")
    assert retrieved.items.root[0].name == "gizmo"
    assert retrieved.items.root[0].qty == 10


def test_rootmodel_strings_save_and_get(dynamo):
    """RootModel[list[str]] round-trips correctly."""
    pk = f"RM_STR#{uuid.uuid4().hex[:8]}"
    TagModel.model_config = ModelConfig(table="test_table", client=dynamo)

    tags = TagList(["python", "rust", "dynamodb"])
    model = TagModel(pk=pk, sk="TAGS", tags=tags)
    model.sync_save()

    retrieved = TagModel.sync_get(pk=pk, sk="TAGS")
    assert isinstance(retrieved.tags, TagList)
    assert retrieved.tags.root == ["python", "rust", "dynamodb"]


def test_arbitrary_type_save_and_get(dynamo):
    """JSONAttribute(list[str]) works with arbitrary types via TypeAdapter."""
    pk = f"ARB#{uuid.uuid4().hex[:8]}"
    ScoreModel.model_config = ModelConfig(table="test_table", client=dynamo)

    model = ScoreModel(pk=pk, sk="SCORES", scores=["high", "medium", "low"])
    model.sync_save()

    retrieved = ScoreModel.sync_get(pk=pk, sk="SCORES")
    assert retrieved.scores == ["high", "medium", "low"]


@MemoryBackend()
def test_rootmodel_inplace_mutation_detected():
    """In-place mutation on RootModel is detected on save."""
    items = ItemList([Item(name="widget", qty=5)])
    inv = Inventory(pk="INV#1", sk="INV", items=items)
    inv.sync_save()

    loaded = Inventory.sync_get(pk="INV#1", sk="INV")
    loaded.items.root.append(Item(name="gadget", qty=2))
    loaded.sync_save()

    result = Inventory.sync_get(pk="INV#1", sk="INV")
    assert len(result.items.root) == 2
    assert result.items.root[1].name == "gadget"
