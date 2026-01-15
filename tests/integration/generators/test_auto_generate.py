"""Integration tests for auto-generate strategies with real DynamoDB."""

import asyncio
import re

import pytest
from pydynox import AutoGenerate, Model, ModelConfig
from pydynox.attributes import NumberAttribute, StringAttribute


def test_auto_generate_ulid_on_save(dynamo):
    """ULID should be generated on save when pk is None."""

    # GIVEN a model with ULID auto-generate on pk
    class Order(Model):
        model_config = ModelConfig(table="test_table", client=dynamo)
        pk = StringAttribute(hash_key=True, default=AutoGenerate.ULID)
        sk = StringAttribute(range_key=True)
        total = NumberAttribute()

    Order._client_instance = None
    order = Order(sk="ORDER#DETAILS", total=100)
    assert order.pk is None

    # WHEN saving
    order.save()

    # THEN pk is generated as ULID and saved
    assert order.pk is not None
    assert len(order.pk) == 26
    loaded = Order.get(pk=order.pk, sk="ORDER#DETAILS")
    assert loaded is not None
    assert loaded.total == 100


def test_auto_generate_uuid4_on_save(dynamo):
    """UUID4 should be generated on save when attribute is None."""

    # GIVEN a model with UUID4 auto-generate on sk
    class Event(Model):
        model_config = ModelConfig(table="test_table", client=dynamo)
        pk = StringAttribute(hash_key=True)
        sk = StringAttribute(range_key=True, default=AutoGenerate.UUID4)
        name = StringAttribute()

    Event._client_instance = None
    event = Event(pk="EVENT#1", name="Test Event")
    assert event.sk is None

    # WHEN saving
    event.save()

    # THEN sk is generated as UUID4 and saved
    assert event.sk is not None
    assert len(event.sk) == 36
    assert event.sk.count("-") == 4
    loaded = Event.get(pk="EVENT#1", sk=event.sk)
    assert loaded is not None
    assert loaded.name == "Test Event"


def test_auto_generate_ksuid_on_save(dynamo):
    """KSUID should be generated on save."""

    # GIVEN a model with KSUID auto-generate
    class Session(Model):
        model_config = ModelConfig(table="test_table", client=dynamo)
        pk = StringAttribute(hash_key=True, default=AutoGenerate.KSUID)
        sk = StringAttribute(range_key=True)

    Session._client_instance = None
    session = Session(sk="SESSION#DATA")

    # WHEN saving
    session.save()

    # THEN pk is generated as KSUID
    assert session.pk is not None
    assert len(session.pk) == 27
    loaded = Session.get(pk=session.pk, sk="SESSION#DATA")
    assert loaded is not None


def test_auto_generate_epoch_on_save(dynamo):
    """EPOCH should generate Unix timestamp in seconds."""

    # GIVEN a model with EPOCH auto-generate
    class Log(Model):
        model_config = ModelConfig(table="test_table", client=dynamo)
        pk = StringAttribute(hash_key=True)
        sk = StringAttribute(range_key=True)
        created_at = NumberAttribute(default=AutoGenerate.EPOCH)

    Log._client_instance = None
    log = Log(pk="LOG#1", sk="ENTRY#1")
    assert log.created_at is None

    # WHEN saving
    log.save()

    # THEN created_at is generated as epoch timestamp
    assert log.created_at is not None
    assert log.created_at > 1700000000  # After 2023
    loaded = Log.get(pk="LOG#1", sk="ENTRY#1")
    assert loaded.created_at == log.created_at


def test_auto_generate_epoch_ms_on_save(dynamo):
    """EPOCH_MS should generate Unix timestamp in milliseconds."""

    # GIVEN a model with EPOCH_MS auto-generate
    class Metric(Model):
        model_config = ModelConfig(table="test_table", client=dynamo)
        pk = StringAttribute(hash_key=True)
        sk = StringAttribute(range_key=True)
        timestamp = NumberAttribute(default=AutoGenerate.EPOCH_MS)

    Metric._client_instance = None
    metric = Metric(pk="METRIC#1", sk="CPU")

    # WHEN saving
    metric.save()

    # THEN timestamp is generated in milliseconds
    assert metric.timestamp is not None
    assert metric.timestamp > 1700000000000  # After 2023 in ms
    loaded = Metric.get(pk="METRIC#1", sk="CPU")
    assert loaded.timestamp == metric.timestamp


def test_auto_generate_iso8601_on_save(dynamo):
    """ISO8601 should generate formatted timestamp string."""

    # GIVEN a model with ISO8601 auto-generate
    class Audit(Model):
        model_config = ModelConfig(table="test_table", client=dynamo)
        pk = StringAttribute(hash_key=True)
        sk = StringAttribute(range_key=True)
        created_at = StringAttribute(default=AutoGenerate.ISO8601)

    Audit._client_instance = None
    audit = Audit(pk="AUDIT#1", sk="ACTION#1")

    # WHEN saving
    audit.save()

    # THEN created_at is ISO8601 formatted
    assert audit.created_at is not None
    pattern = r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$"
    assert re.match(pattern, audit.created_at)
    loaded = Audit.get(pk="AUDIT#1", sk="ACTION#1")
    assert loaded.created_at == audit.created_at


def test_auto_generate_skipped_when_value_provided(dynamo):
    """Auto-generate should NOT run when value is provided."""

    # GIVEN a model with auto-generate and an explicit value
    class Item(Model):
        model_config = ModelConfig(table="test_table", client=dynamo)
        pk = StringAttribute(hash_key=True, default=AutoGenerate.ULID)
        sk = StringAttribute(range_key=True)

    Item._client_instance = None
    item = Item(pk="CUSTOM#ID", sk="DATA")

    # WHEN saving
    item.save()

    # THEN provided value is used, not generated
    assert item.pk == "CUSTOM#ID"
    loaded = Item.get(pk="CUSTOM#ID", sk="DATA")
    assert loaded is not None


def test_auto_generate_multiple_fields(dynamo):
    """Multiple fields can have auto-generate strategies."""

    # GIVEN a model with multiple auto-generate fields
    class Record(Model):
        model_config = ModelConfig(table="test_table", client=dynamo)
        pk = StringAttribute(hash_key=True, default=AutoGenerate.ULID)
        sk = StringAttribute(range_key=True, default=AutoGenerate.UUID4)
        created_at = StringAttribute(default=AutoGenerate.ISO8601)
        timestamp = NumberAttribute(default=AutoGenerate.EPOCH_MS)

    Record._client_instance = None
    record = Record()

    # WHEN saving
    record.save()

    # THEN all fields are generated
    assert record.pk is not None
    assert len(record.pk) == 26  # ULID
    assert record.sk is not None
    assert len(record.sk) == 36  # UUID4
    assert record.created_at is not None
    assert "T" in record.created_at  # ISO8601
    assert record.timestamp is not None
    assert record.timestamp > 1700000000000  # EPOCH_MS

    loaded = Record.get(pk=record.pk, sk=record.sk)
    assert loaded is not None
    assert loaded.created_at == record.created_at
    assert loaded.timestamp == record.timestamp


@pytest.mark.asyncio
async def test_auto_generate_concurrent_async_saves(dynamo):
    """Auto-generate should be thread-safe with concurrent async saves."""

    # GIVEN a model with auto-generate on pk and sk
    class ConcurrentOrder(Model):
        model_config = ModelConfig(table="test_table", client=dynamo)
        pk = StringAttribute(hash_key=True, default=AutoGenerate.ULID)
        sk = StringAttribute(range_key=True, default=AutoGenerate.UUID4)
        seq = NumberAttribute()

    ConcurrentOrder._client_instance = None

    async def create_order(seq: int) -> ConcurrentOrder:
        order = ConcurrentOrder(seq=seq)
        await order.async_save()
        return order

    # WHEN creating 50 orders concurrently
    tasks = [create_order(i) for i in range(50)]
    orders = await asyncio.gather(*tasks)

    # THEN all orders have unique pks and sks
    pks = [o.pk for o in orders]
    assert len(set(pks)) == 50, "All pks should be unique"
    sks = [o.sk for o in orders]
    assert len(set(sks)) == 50, "All sks should be unique"

    for order in orders:
        assert len(order.pk) == 26  # ULID
        assert len(order.sk) == 36  # UUID4

    # AND all are saved to DynamoDB
    for order in orders:
        loaded = await ConcurrentOrder.async_get(pk=order.pk, sk=order.sk)
        assert loaded is not None
        assert loaded.seq == order.seq


@pytest.mark.asyncio
async def test_auto_generate_high_concurrency(dynamo):
    """Stress test: 200 concurrent saves should all get unique IDs."""

    # GIVEN a model with ULID auto-generate
    class StressItem(Model):
        model_config = ModelConfig(table="test_table", client=dynamo)
        pk = StringAttribute(hash_key=True, default=AutoGenerate.ULID)
        sk = StringAttribute(range_key=True)
        batch = NumberAttribute()

    StressItem._client_instance = None

    async def create_item(batch: int, idx: int) -> str:
        item = StressItem(sk=f"STRESS#{batch}#{idx}", batch=batch)
        await item.async_save()
        return item.pk

    # WHEN creating 200 items concurrently
    tasks = [create_item(1, i) for i in range(200)]
    pks = await asyncio.gather(*tasks)

    # THEN all 200 have unique pks
    assert len(set(pks)) == 200, f"Expected 200 unique pks, got {len(set(pks))}"
