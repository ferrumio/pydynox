"""Integration tests for transact_write operation.

Tests transaction success and rollback behavior.
Requirements: 9.3, 9.4
"""

import pytest
from pydynox import Model, ModelConfig, SyncTransaction, Transaction
from pydynox.attributes import StringAttribute, VersionAttribute
from pydynox.exceptions import PydynoxException, TransactionCanceledException


class VersionedItem(Model):
    model_config = ModelConfig(table="test_table")
    pk = StringAttribute(partition_key=True)
    sk = StringAttribute(sort_key=True)
    name = StringAttribute()
    version = VersionAttribute()


@pytest.fixture
def versioned_model(dynamo):
    VersionedItem.model_config = ModelConfig(table="test_table", client=dynamo)
    return VersionedItem


@pytest.mark.asyncio
async def test_transact_write_puts_multiple_items(dynamo):
    """Test transaction with multiple put operations."""
    # GIVEN multiple items to put
    operations = [
        {
            "type": "put",
            "table": "test_table",
            "item": {"pk": "TXN#1", "sk": "ITEM#1", "name": "Alice"},
        },
        {
            "type": "put",
            "table": "test_table",
            "item": {"pk": "TXN#1", "sk": "ITEM#2", "name": "Bob"},
        },
        {
            "type": "put",
            "table": "test_table",
            "item": {"pk": "TXN#1", "sk": "ITEM#3", "name": "Charlie"},
        },
    ]

    # WHEN we execute the transaction
    await dynamo.transact_write(operations)

    # THEN all items are saved
    for op in operations:
        item = op["item"]
        key = {"pk": item["pk"], "sk": item["sk"]}
        result = await dynamo.get_item("test_table", key)
        assert result is not None
        assert result["name"] == item["name"]


@pytest.mark.asyncio
async def test_transact_write_with_delete(dynamo):
    """Test transaction with put and delete operations."""
    # First, put an item to delete later
    await dynamo.put_item("test_table", {"pk": "TXN#2", "sk": "DELETE", "name": "ToDelete"})

    operations = [
        {
            "type": "put",
            "table": "test_table",
            "item": {"pk": "TXN#2", "sk": "NEW#1", "name": "NewItem"},
        },
        {
            "type": "delete",
            "table": "test_table",
            "key": {"pk": "TXN#2", "sk": "DELETE"},
        },
    ]

    await dynamo.transact_write(operations)

    # Verify new item exists
    result = await dynamo.get_item("test_table", {"pk": "TXN#2", "sk": "NEW#1"})
    assert result is not None
    assert result["name"] == "NewItem"

    # Verify deleted item is gone
    result = await dynamo.get_item("test_table", {"pk": "TXN#2", "sk": "DELETE"})
    assert result is None


@pytest.mark.asyncio
async def test_transact_write_with_update(dynamo):
    """Test transaction with update operation."""
    # First, put an item to update
    await dynamo.put_item("test_table", {"pk": "TXN#3", "sk": "UPDATE", "counter": 10})

    operations = [
        {
            "type": "update",
            "table": "test_table",
            "key": {"pk": "TXN#3", "sk": "UPDATE"},
            "update_expression": "SET #c = #c + :val",
            "expression_attribute_names": {"#c": "counter"},
            "expression_attribute_values": {":val": 5},
        },
    ]

    await dynamo.transact_write(operations)

    # Verify update was applied
    result = await dynamo.get_item("test_table", {"pk": "TXN#3", "sk": "UPDATE"})
    assert result is not None
    assert result["counter"] == 15


@pytest.mark.asyncio
async def test_transact_write_rollback_on_condition_failure(dynamo):
    """Test that transaction rolls back all operations when a condition fails.

    Requirements: 9.4
    """
    # GIVEN initial items
    await dynamo.put_item("test_table", {"pk": "TXN#4", "sk": "ITEM#1", "value": "original"})
    await dynamo.put_item("test_table", {"pk": "TXN#4", "sk": "CHECK", "status": "inactive"})

    # AND a transaction with a condition check that will fail
    operations = [
        {
            "type": "put",
            "table": "test_table",
            "item": {"pk": "TXN#4", "sk": "ITEM#1", "value": "updated"},
        },
        {
            "type": "condition_check",
            "table": "test_table",
            "key": {"pk": "TXN#4", "sk": "CHECK"},
            "condition_expression": "#s = :expected",
            "expression_attribute_names": {"#s": "status"},
            "expression_attribute_values": {":expected": "active"},  # Will fail
        },
    ]

    # WHEN we execute the transaction
    # THEN it fails
    with pytest.raises((TransactionCanceledException, PydynoxException)):
        await dynamo.transact_write(operations)

    # AND the put was rolled back - original value remains
    result = await dynamo.get_item("test_table", {"pk": "TXN#4", "sk": "ITEM#1"})
    assert result is not None
    assert result["value"] == "original"


@pytest.mark.asyncio
async def test_transact_write_condition_check_success(dynamo):
    """Test transaction with a passing condition check."""
    # Put initial items
    await dynamo.put_item("test_table", {"pk": "TXN#5", "sk": "CHECK", "status": "active"})

    operations = [
        {
            "type": "put",
            "table": "test_table",
            "item": {"pk": "TXN#5", "sk": "NEW", "name": "Created"},
        },
        {
            "type": "condition_check",
            "table": "test_table",
            "key": {"pk": "TXN#5", "sk": "CHECK"},
            "condition_expression": "#s = :expected",
            "expression_attribute_names": {"#s": "status"},
            "expression_attribute_values": {":expected": "active"},
        },
    ]

    await dynamo.transact_write(operations)

    # Verify the put succeeded
    result = await dynamo.get_item("test_table", {"pk": "TXN#5", "sk": "NEW"})
    assert result is not None
    assert result["name"] == "Created"


@pytest.mark.asyncio
async def test_transaction_context_manager(dynamo):
    """Test Transaction async context manager commits on exit."""
    # WHEN we use the async context manager
    async with Transaction(dynamo) as txn:
        txn.put("test_table", {"pk": "TXN#6", "sk": "ITEM#1", "name": "Alice"})
        txn.put("test_table", {"pk": "TXN#6", "sk": "ITEM#2", "name": "Bob"})

    # THEN items are saved
    result = await dynamo.get_item("test_table", {"pk": "TXN#6", "sk": "ITEM#1"})
    assert result is not None
    assert result["name"] == "Alice"

    result = await dynamo.get_item("test_table", {"pk": "TXN#6", "sk": "ITEM#2"})
    assert result is not None
    assert result["name"] == "Bob"


@pytest.mark.asyncio
async def test_transaction_context_manager_rollback_on_exception(dynamo):
    """Test Transaction async context manager does not commit on exception."""
    # GIVEN an existing item
    await dynamo.put_item("test_table", {"pk": "TXN#7", "sk": "ITEM", "value": "original"})

    # WHEN an exception occurs in the context
    try:
        async with Transaction(dynamo) as txn:
            txn.put("test_table", {"pk": "TXN#7", "sk": "ITEM", "value": "updated"})
            raise RuntimeError("Simulated error")
    except RuntimeError:
        pass

    # THEN the put was NOT committed - original value remains
    result = await dynamo.get_item("test_table", {"pk": "TXN#7", "sk": "ITEM"})
    assert result is not None
    assert result["value"] == "original"


@pytest.mark.asyncio
async def test_transact_write_empty_operations(dynamo):
    """Test transaction with empty operations list does nothing."""
    # Should not raise an error
    await dynamo.transact_write([])


def test_sync_transaction_context_manager(dynamo):
    """Test SyncTransaction context manager commits on exit."""
    # WHEN we use the sync context manager
    with SyncTransaction(dynamo) as txn:
        txn.put("test_table", {"pk": "TXN#8", "sk": "ITEM#1", "name": "Alice"})
        txn.put("test_table", {"pk": "TXN#8", "sk": "ITEM#2", "name": "Bob"})

    # THEN items are saved
    result = dynamo.sync_get_item("test_table", {"pk": "TXN#8", "sk": "ITEM#1"})
    assert result is not None
    assert result["name"] == "Alice"

    result = dynamo.sync_get_item("test_table", {"pk": "TXN#8", "sk": "ITEM#2"})
    assert result is not None
    assert result["name"] == "Bob"


@pytest.mark.asyncio
async def test_save_model_updates_version_after_commit(versioned_model, dynamo):
    """save_model bumps version attribute after successful commit."""
    # GIVEN a saved model with version=1
    item = versioned_model(pk="ASYNC_TXN_MODEL#1", sk="DOC#1", name="Alice")
    await item.save()
    assert item.version == 1

    # WHEN we update via transaction using save_model
    item.name = "Bob"
    async with Transaction(dynamo) as txn:
        txn.save_model(item)

    # THEN version is bumped locally
    assert item.version == 2

    # AND the DB has the updated data
    loaded = await versioned_model.get(pk="ASYNC_TXN_MODEL#1", sk="DOC#1")
    assert loaded is not None
    assert loaded.name == "Bob"
    assert loaded.version == 2


@pytest.mark.asyncio
async def test_save_model_allows_subsequent_save(versioned_model, dynamo):
    """After save_model commit, a follow-up save works (no stale version)."""
    # GIVEN a model saved via transaction
    item = versioned_model(pk="ASYNC_TXN_MODEL#2", sk="DOC#1", name="Alice")
    await item.save()

    item.name = "Bob"
    async with Transaction(dynamo) as txn:
        txn.save_model(item)

    assert item.version == 2

    # WHEN we do a regular save after the transaction
    item.name = "Charlie"
    await item.save()

    # THEN it succeeds with version=3
    assert item.version == 3
    loaded = await versioned_model.get(pk="ASYNC_TXN_MODEL#2", sk="DOC#1")
    assert loaded is not None
    assert loaded.name == "Charlie"
    assert loaded.version == 3


@pytest.mark.asyncio
async def test_save_model_multiple_models_in_transaction(versioned_model, dynamo):
    """Multiple models in one transaction all get version updates."""
    # GIVEN two models
    item1 = versioned_model(pk="ASYNC_TXN_MODEL#3", sk="DOC#1", name="Alice")
    item2 = versioned_model(pk="ASYNC_TXN_MODEL#3", sk="DOC#2", name="Bob")
    await item1.save()
    await item2.save()

    # WHEN both are saved in a single transaction
    item1.name = "Alice Updated"
    item2.name = "Bob Updated"
    async with Transaction(dynamo) as txn:
        txn.save_model(item1)
        txn.save_model(item2)

    # THEN both versions are bumped
    assert item1.version == 2
    assert item2.version == 2


@pytest.mark.asyncio
async def test_delete_model_in_transaction(versioned_model, dynamo):
    """delete_model removes the item from DynamoDB."""
    # GIVEN a saved model
    item = versioned_model(pk="ASYNC_TXN_MODEL#4", sk="DOC#1", name="Alice")
    await item.save()

    # WHEN we delete via transaction
    async with Transaction(dynamo) as txn:
        txn.delete_model(item)

    # THEN item is gone from DB
    loaded = await versioned_model.get(pk="ASYNC_TXN_MODEL#4", sk="DOC#1")
    assert loaded is None


@pytest.mark.asyncio
async def test_save_model_without_version_attribute(dynamo):
    """save_model works for models without VersionAttribute."""

    class SimpleItem(Model):
        model_config = ModelConfig(table="test_table", client=dynamo)
        pk = StringAttribute(partition_key=True)
        sk = StringAttribute(sort_key=True)
        name = StringAttribute()

    item = SimpleItem(pk="ASYNC_TXN_MODEL#5", sk="DOC#1", name="Alice")

    async with Transaction(dynamo) as txn:
        txn.save_model(item)

    loaded = await dynamo.get_item("test_table", {"pk": "ASYNC_TXN_MODEL#5", "sk": "DOC#1"})
    assert loaded is not None
    assert loaded["name"] == "Alice"
