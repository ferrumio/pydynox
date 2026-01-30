"""Integration tests for optimistic locking with VersionAttribute."""

import asyncio

import pytest
from pydynox import Model, ModelConfig
from pydynox.attributes import StringAttribute, VersionAttribute
from pydynox.exceptions import ConditionalCheckFailedException


class VersionedDoc(Model):
    """Test model with version attribute."""

    model_config = ModelConfig(table="test_table")
    pk = StringAttribute(partition_key=True)
    sk = StringAttribute(sort_key=True)
    content = StringAttribute()
    version = VersionAttribute()


@pytest.fixture
def versioned_model(dynamo):
    """Bind client to model."""
    VersionedDoc.model_config = ModelConfig(table="test_table", client=dynamo)
    return VersionedDoc


@pytest.mark.asyncio
async def test_version_starts_at_one(versioned_model):
    """First save sets version to 1."""
    # GIVEN a new document
    doc = versioned_model(pk="VERSION#1", sk="DOC#1", content="Hello")
    assert doc.version is None

    # WHEN we save it
    await doc.save()

    # THEN version is set to 1
    assert doc.version == 1


@pytest.mark.asyncio
async def test_version_increments_on_save(versioned_model):
    """Each save increments version."""
    # GIVEN a document
    doc = versioned_model(pk="VERSION#2", sk="DOC#1", content="Hello")
    await doc.save()
    assert doc.version == 1

    # WHEN we save again
    doc.content = "Updated"
    await doc.save()

    # THEN version increments
    assert doc.version == 2

    # AND again
    doc.content = "Updated again"
    await doc.save()
    assert doc.version == 3


@pytest.mark.asyncio
async def test_version_loaded_from_db(versioned_model):
    """Version is loaded correctly from DynamoDB."""
    doc = versioned_model(pk="VERSION#3", sk="DOC#1", content="Hello")
    await doc.save()
    await doc.save()  # version = 2

    loaded = await versioned_model.get(pk="VERSION#3", sk="DOC#1")
    assert loaded is not None
    assert loaded.version == 2


@pytest.mark.asyncio
async def test_concurrent_update_fails(versioned_model):
    """Concurrent updates fail with ConditionalCheckFailedException."""
    # GIVEN a document
    doc = versioned_model(pk="VERSION#4", sk="DOC#1", content="Original")
    await doc.save()

    # AND two clients load the same document
    doc1 = await versioned_model.get(pk="VERSION#4", sk="DOC#1")
    doc2 = await versioned_model.get(pk="VERSION#4", sk="DOC#1")

    assert doc1 is not None
    assert doc2 is not None
    assert doc1.version == 1
    assert doc2.version == 1

    # WHEN first client updates
    doc1.content = "Update from client 1"
    await doc1.save()
    assert doc1.version == 2

    # THEN second client's update fails (version mismatch)
    doc2.content = "Update from client 2"
    with pytest.raises(ConditionalCheckFailedException):
        await doc2.save()


@pytest.mark.asyncio
async def test_delete_with_version_check(versioned_model):
    """Delete checks version before deleting."""
    doc = versioned_model(pk="VERSION#5", sk="DOC#1", content="To delete")
    await doc.save()
    await doc.save()  # version = 2

    # Load stale copy
    stale = await versioned_model.get(pk="VERSION#5", sk="DOC#1")
    assert stale is not None

    # Update the document (version becomes 3)
    doc.content = "Updated"
    await doc.save()
    assert doc.version == 3

    # Delete with stale version fails
    with pytest.raises(ConditionalCheckFailedException):
        await stale.delete()

    # Delete with current version succeeds
    await doc.delete()

    # Verify deleted
    assert await versioned_model.get(pk="VERSION#5", sk="DOC#1") is None


@pytest.mark.asyncio
async def test_new_item_fails_if_exists(versioned_model):
    """Creating new item fails if item already exists."""
    # Create first document
    doc1 = versioned_model(pk="VERSION#6", sk="DOC#1", content="First")
    await doc1.save()

    # Try to create another with same key (version=None means new)
    doc2 = versioned_model(pk="VERSION#6", sk="DOC#1", content="Second")
    with pytest.raises(ConditionalCheckFailedException):
        await doc2.save()


@pytest.mark.asyncio
async def test_version_with_user_condition(versioned_model):
    """User condition is combined with version condition."""
    doc = versioned_model(pk="VERSION#7", sk="DOC#1", content="Hello")
    await doc.save()
    assert doc.version == 1

    # Reload to get fresh version
    doc = await versioned_model.get(pk="VERSION#7", sk="DOC#1")
    assert doc is not None

    # Add user condition that fails
    doc.content = "Updated"
    with pytest.raises(ConditionalCheckFailedException):
        await doc.save(condition=VersionedDoc.content == "Wrong")

    # Reload again since version was incremented locally
    doc = await versioned_model.get(pk="VERSION#7", sk="DOC#1")
    assert doc is not None
    assert doc.version == 1  # Still 1 because save failed

    # Add user condition that passes
    doc.content = "Updated"
    await doc.save(condition=VersionedDoc.content == "Hello")
    assert doc.version == 2


# ========== HIGH CONCURRENCY TESTS ==========


@pytest.mark.asyncio
async def test_high_concurrency_only_one_wins(versioned_model):
    """High concurrency: Only one concurrent save succeeds per version."""
    # Create initial document
    doc = versioned_model(pk="CONCURRENT#1", sk="DOC#1", content="Original")
    await doc.save()

    num_concurrent = 10

    # Load all documents FIRST, then save concurrently
    # This ensures all workers have the same version
    loaded_docs = []
    for i in range(num_concurrent):
        loaded = await versioned_model.get(pk="CONCURRENT#1", sk="DOC#1")
        assert loaded is not None
        loaded.content = f"Updated by worker {i}"
        loaded_docs.append(loaded)

    # All should have version 1
    for d in loaded_docs:
        assert d.version == 1

    success_count = 0
    failure_count = 0

    async def try_save(doc_to_save):
        nonlocal success_count, failure_count
        try:
            await doc_to_save.save()
            success_count += 1
        except ConditionalCheckFailedException:
            failure_count += 1

    # Run all saves concurrently
    await asyncio.gather(*[try_save(d) for d in loaded_docs])

    # Only one should succeed
    assert success_count == 1
    assert failure_count == num_concurrent - 1

    # Verify final state
    final = await versioned_model.get(pk="CONCURRENT#1", sk="DOC#1")
    assert final is not None
    assert final.version == 2


@pytest.mark.asyncio
async def test_high_concurrency_sequential_updates(versioned_model):
    """High concurrency: Sequential updates with retry all succeed."""
    doc = versioned_model(pk="CONCURRENT#2", sk="DOC#1", content="Original")
    await doc.save()

    num_workers = 5
    updates_per_worker = 3
    total_updates = num_workers * updates_per_worker

    async def update_with_retry(worker_id: int):
        for i in range(updates_per_worker):
            max_retries = 10
            for attempt in range(max_retries):
                loaded = await versioned_model.get(pk="CONCURRENT#2", sk="DOC#1")
                if loaded is None:
                    return

                loaded.content = f"Worker {worker_id}, update {i}, attempt {attempt}"
                try:
                    await loaded.save()
                    break
                except ConditionalCheckFailedException:
                    if attempt == max_retries - 1:
                        raise
                    await asyncio.sleep(0.01)  # Small delay before retry

    await asyncio.gather(*[update_with_retry(i) for i in range(num_workers)])

    final = await versioned_model.get(pk="CONCURRENT#2", sk="DOC#1")
    assert final is not None
    assert final.version == 1 + total_updates


@pytest.mark.asyncio
async def test_high_concurrency_new_item_race(versioned_model):
    """High concurrency: Only one create succeeds for same key."""
    num_concurrent = 10
    success_count = 0
    failure_count = 0

    async def try_create(worker_id: int):
        nonlocal success_count, failure_count
        doc = versioned_model(
            pk="CONCURRENT#3",
            sk="DOC#1",
            content=f"Created by worker {worker_id}",
        )
        try:
            await doc.save()
            success_count += 1
        except ConditionalCheckFailedException:
            failure_count += 1

    await asyncio.gather(*[try_create(i) for i in range(num_concurrent)])

    # Only one create should succeed
    assert success_count == 1
    assert failure_count == num_concurrent - 1

    final = await versioned_model.get(pk="CONCURRENT#3", sk="DOC#1")
    assert final is not None
    assert final.version == 1


@pytest.mark.asyncio
async def test_high_concurrency_mixed_operations(versioned_model):
    """High concurrency: Mix of saves and deletes."""
    doc = versioned_model(pk="CONCURRENT#4", sk="DOC#1", content="Original")
    await doc.save()

    delete_success = False
    save_after_delete_failures = 0

    async def try_delete():
        nonlocal delete_success
        loaded = await versioned_model.get(pk="CONCURRENT#4", sk="DOC#1")
        if loaded:
            try:
                await loaded.delete()
                delete_success = True
            except ConditionalCheckFailedException:
                pass

    async def try_save(worker_id: int):
        nonlocal save_after_delete_failures
        loaded = await versioned_model.get(pk="CONCURRENT#4", sk="DOC#1")
        if loaded:
            loaded.content = f"Updated by {worker_id}"
            try:
                await loaded.save()
            except ConditionalCheckFailedException:
                save_after_delete_failures += 1

    # Run delete and saves concurrently
    tasks = [try_delete()] + [try_save(i) for i in range(5)]
    await asyncio.gather(*tasks)

    # Either delete succeeded or some saves succeeded
    # The important thing is no data corruption
    final = await versioned_model.get(pk="CONCURRENT#4", sk="DOC#1")
    if delete_success:
        # If delete won, item should be gone or recreated
        pass  # Item may or may not exist
    else:
        # If saves won, item should exist with incremented version
        assert final is not None
        assert final.version >= 2
