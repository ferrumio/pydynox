"""Integration tests for hot partition detection."""

import logging
import uuid

import pytest
from pydynox import DynamoDBClient
from pydynox.diagnostics import HotPartitionDetector


@pytest.fixture
def detector():
    """Create a detector with low thresholds for testing."""
    return HotPartitionDetector(
        writes_threshold=5,
        reads_threshold=5,
        window_seconds=60,
    )


@pytest.fixture
def client_with_detector(localstack_endpoint, detector):
    """Create a client with hot partition detection enabled."""
    return DynamoDBClient(
        region="us-east-1",
        endpoint_url=localstack_endpoint,
        access_key="testing",
        secret_key="testing",
        diagnostics=detector,
    )


@pytest.mark.asyncio
async def test_put_item_tracks_writes(client_with_detector, detector, _create_table):
    """put_item operations are tracked for hot partition detection."""
    # GIVEN a client with hot partition detection
    pk = f"HOT#{uuid.uuid4()}"

    # WHEN putting 3 items with same pk
    for i in range(3):
        await client_with_detector.put_item(
            "test_table",
            {"pk": pk, "sk": f"ITEM#{i}", "data": "test"},
        )

    # THEN writes are tracked
    assert detector.get_write_count("test_table", pk) == 3


@pytest.mark.asyncio
async def test_get_item_tracks_reads(client_with_detector, detector, _create_table):
    """get_item operations are tracked for hot partition detection."""
    # GIVEN an existing item
    pk = f"HOT#{uuid.uuid4()}"
    await client_with_detector.put_item(
        "test_table",
        {"pk": pk, "sk": "ITEM#1", "data": "test"},
    )

    # WHEN reading it multiple times
    for _ in range(3):
        await client_with_detector.get_item("test_table", {"pk": pk, "sk": "ITEM#1"})

    # THEN reads are tracked
    assert detector.get_read_count("test_table", pk) == 3


@pytest.mark.asyncio
async def test_update_item_tracks_writes(client_with_detector, detector, _create_table):
    """update_item operations are tracked for hot partition detection."""
    # GIVEN an existing item
    pk = f"HOT#{uuid.uuid4()}"
    await client_with_detector.put_item(
        "test_table",
        {"pk": pk, "sk": "ITEM#1", "data": "test"},
    )

    # WHEN updating it multiple times
    for i in range(3):
        await client_with_detector.update_item(
            "test_table",
            {"pk": pk, "sk": "ITEM#1"},
            updates={"data": f"updated-{i}"},
        )

    # THEN writes are tracked (1 put + 3 updates = 4)
    assert detector.get_write_count("test_table", pk) == 4


@pytest.mark.asyncio
async def test_delete_item_tracks_writes(client_with_detector, detector, _create_table):
    """delete_item operations are tracked for hot partition detection."""
    # GIVEN existing items
    pk = f"HOT#{uuid.uuid4()}"
    for i in range(3):
        await client_with_detector.put_item(
            "test_table",
            {"pk": pk, "sk": f"ITEM#{i}", "data": "test"},
        )

    # WHEN deleting them
    for i in range(3):
        await client_with_detector.delete_item("test_table", {"pk": pk, "sk": f"ITEM#{i}"})

    # THEN writes are tracked (3 puts + 3 deletes >= 5)
    assert detector.get_write_count("test_table", pk) >= 5


@pytest.mark.asyncio
async def test_logs_warning_on_hot_partition(client_with_detector, detector, _create_table, caplog):
    """Logs warning when partition becomes hot."""
    # GIVEN a client with threshold=5
    pk = f"HOT#{uuid.uuid4()}"

    # WHEN writing 6 items (exceeds threshold)
    with caplog.at_level(logging.WARNING, logger="pydynox.diagnostics"):
        for i in range(6):
            await client_with_detector.put_item(
                "test_table",
                {"pk": pk, "sk": f"ITEM#{i}", "data": "test"},
            )

    # THEN warning is logged
    assert "Hot partition detected" in caplog.text
    assert pk in caplog.text


@pytest.mark.asyncio
async def test_different_pks_tracked_separately(client_with_detector, detector, _create_table):
    """Different partition keys are tracked separately."""
    # GIVEN two different pks
    pk1 = f"HOT1#{uuid.uuid4()}"
    pk2 = f"HOT2#{uuid.uuid4()}"

    # WHEN writing to each
    for i in range(3):
        await client_with_detector.put_item(
            "test_table",
            {"pk": pk1, "sk": f"ITEM#{i}", "data": "test"},
        )
    for i in range(2):
        await client_with_detector.put_item(
            "test_table",
            {"pk": pk2, "sk": f"ITEM#{i}", "data": "test"},
        )

    # THEN each is tracked separately
    assert detector.get_write_count("test_table", pk1) == 3
    assert detector.get_write_count("test_table", pk2) == 2


@pytest.mark.asyncio
async def test_client_without_detector_works(dynamo, _create_table):
    """Client without detector still works normally."""
    # GIVEN a client without detector
    pk = f"NORMAL#{uuid.uuid4()}"

    # WHEN using it normally
    await dynamo.put_item(
        "test_table",
        {"pk": pk, "sk": "ITEM#1", "data": "test"},
    )
    result = await dynamo.get_item("test_table", {"pk": pk, "sk": "ITEM#1"})

    # THEN operations work
    assert result is not None
    assert result["data"] == "test"


@pytest.mark.asyncio
async def test_table_override_prevents_warning(
    client_with_detector, detector, _create_table, caplog
):
    """Table override with higher threshold prevents warning."""
    # GIVEN a higher threshold for test_table
    pk = f"HOT#{uuid.uuid4()}"
    detector.set_table_thresholds("test_table", writes_threshold=100)

    # WHEN writing 10 items
    with caplog.at_level(logging.WARNING, logger="pydynox.diagnostics"):
        for i in range(10):
            await client_with_detector.put_item(
                "test_table",
                {"pk": pk, "sk": f"ITEM#{i}", "data": "test"},
            )

    # THEN no warning because threshold is 100
    assert "Hot partition detected" not in caplog.text


@pytest.mark.asyncio
async def test_model_config_overrides_client_threshold(
    client_with_detector, detector, _create_table, caplog
):
    """ModelConfig hot_partition_writes/reads overrides client's detector threshold."""
    # GIVEN a model with higher threshold than client
    from pydynox import Model, ModelConfig
    from pydynox.attributes import StringAttribute

    class HighTrafficModel(Model):
        model_config = ModelConfig(
            table="test_table",
            client=client_with_detector,
            hot_partition_writes=50,
            hot_partition_reads=50,
        )
        pk = StringAttribute(partition_key=True)
        sk = StringAttribute(sort_key=True)
        data = StringAttribute()

    pk = f"MODEL#{uuid.uuid4()}"

    # WHEN writing 10 items
    with caplog.at_level(logging.WARNING, logger="pydynox.diagnostics"):
        for i in range(10):
            item = HighTrafficModel(pk=pk, sk=f"ITEM#{i}", data="test")
            await item.save()

    # THEN no warning because model threshold (50) > writes (10)
    assert "Hot partition detected" not in caplog.text
    assert detector.get_write_count("test_table", pk) == 10


@pytest.mark.asyncio
async def test_model_config_lower_threshold_triggers_warning(
    client_with_detector, detector, _create_table, caplog
):
    """ModelConfig with lower threshold triggers warning before client threshold."""
    # GIVEN a model with lower threshold than client
    from pydynox import Model, ModelConfig
    from pydynox.attributes import StringAttribute

    class LowThresholdModel(Model):
        model_config = ModelConfig(
            table="test_table",
            client=client_with_detector,
            hot_partition_writes=3,
        )
        pk = StringAttribute(partition_key=True)
        sk = StringAttribute(sort_key=True)
        data = StringAttribute()

    pk = f"LOW#{uuid.uuid4()}"

    # WHEN writing 4 items
    with caplog.at_level(logging.WARNING, logger="pydynox.diagnostics"):
        for i in range(4):
            item = LowThresholdModel(pk=pk, sk=f"ITEM#{i}", data="test")
            await item.save()

    # THEN warning because model threshold (3) < writes (4)
    assert "Hot partition detected" in caplog.text
    assert pk in caplog.text
