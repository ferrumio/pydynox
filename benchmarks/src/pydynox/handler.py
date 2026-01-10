"""Benchmark Lambda handler for pydynox using Powertools for AWS Lambda."""

from __future__ import annotations

import os
import time
from typing import Any

from aws_lambda_powertools import Logger, Metrics
from aws_lambda_powertools.metrics import MetricResolution, MetricUnit
from aws_lambda_powertools.utilities.typing import LambdaContext
from pydynox import (
    BatchWriter,
    DynamoDBClient,
    Model,
    ModelConfig,
    set_default_client,
)
from pydynox.attributes import (
    CompressedAttribute,
    EncryptedAttribute,
    NumberAttribute,
    S3Attribute,
    S3File,
    StringAttribute,
)

logger = Logger()
metrics = Metrics()

TABLE_NAME = os.environ["TABLE_NAME"]
BUCKET_NAME = os.environ["BUCKET_NAME"]
KMS_KEY_ID = os.environ["KMS_KEY_ID"]
MEMORY_SIZE = os.environ["MEMORY_SIZE"]
ARCHITECTURE = os.environ["ARCHITECTURE"]

# Unique prefix per Lambda config to avoid conflicts when running in parallel
PK_PREFIX = f"PYDYNOX#{MEMORY_SIZE}#{ARCHITECTURE}"

# Create and set default client
client = DynamoDBClient()
set_default_client(client)


# Define models like customers would
class BenchmarkItem(Model):
    model_config = ModelConfig(table=TABLE_NAME)

    pk = StringAttribute(hash_key=True)
    sk = StringAttribute(range_key=True)
    data = StringAttribute(default="")
    num = NumberAttribute(default=0)


class EncryptedItem(Model):
    model_config = ModelConfig(table=TABLE_NAME)

    pk = StringAttribute(hash_key=True)
    sk = StringAttribute(range_key=True)
    secret = EncryptedAttribute(key_id=KMS_KEY_ID)


class CompressedItem(Model):
    model_config = ModelConfig(table=TABLE_NAME)

    pk = StringAttribute(hash_key=True)
    sk = StringAttribute(range_key=True)
    data = CompressedAttribute()


class S3Item(Model):
    model_config = ModelConfig(table=TABLE_NAME)

    pk = StringAttribute(hash_key=True)
    sk = StringAttribute(range_key=True)
    large_data = S3Attribute(bucket=BUCKET_NAME)


def measure_and_publish(operation: str, func, iterations: int = 100) -> None:
    """Run function multiple times and publish each latency to CloudWatch."""
    for _ in range(iterations):
        start = time.perf_counter()
        func()
        end = time.perf_counter()
        latency_ms = (end - start) * 1000
        metrics.add_metric(
            name=operation,
            unit=MetricUnit.Milliseconds,
            value=latency_ms,
            resolution=MetricResolution.High,
        )


def run_basic_benchmarks() -> None:
    """Run basic operation benchmarks."""
    # Setup - create test items
    for i in range(100):
        item = BenchmarkItem(pk=f"{PK_PREFIX}#basic", sk=f"ITEM#{i:04d}", data=f"value_{i}", num=i)
        item.save()

    # put_item (save)
    counter = [0]

    def do_put():
        counter[0] += 1
        item = BenchmarkItem(pk=f"{PK_PREFIX}#put", sk=f"ITEM#{counter[0]:04d}", data="test")
        item.save()

    measure_and_publish("put_item", do_put)

    # get_item
    measure_and_publish(
        "get_item", lambda: BenchmarkItem.get(pk=f"{PK_PREFIX}#basic", sk="ITEM#0050")
    )

    # update_item (using update_by_key - single call, no fetch)
    def do_update():
        BenchmarkItem.update_by_key(pk=f"{PK_PREFIX}#basic", sk="ITEM#0050", data="updated")

    measure_and_publish("update_item", do_update)

    # delete_item (using delete_by_key - single call, no fetch)
    counter[0] = 0

    def do_delete():
        counter[0] += 1
        BenchmarkItem.delete_by_key(pk=f"{PK_PREFIX}#put", sk=f"ITEM#{counter[0]:04d}")

    measure_and_publish("delete_item", do_delete)

    # query (returns Model instances)
    measure_and_publish(
        "query",
        lambda: list(BenchmarkItem.query(f"{PK_PREFIX}#basic", limit=10)),
        iterations=10,
    )

    # query_as_dict (returns plain dicts - faster, comparable to boto3/pynamodb)
    measure_and_publish(
        "query_as_dict",
        lambda: list(BenchmarkItem.query(f"{PK_PREFIX}#basic", limit=10, as_dict=True)),
        iterations=10,
    )


def run_batch_benchmarks() -> None:
    """Run batch operation benchmarks."""
    counter = [0]

    def do_batch_write():
        counter[0] += 25
        with BatchWriter(client, TABLE_NAME) as batch:
            for i in range(25):
                batch.put(
                    {
                        "pk": f"{PK_PREFIX}#batch",
                        "sk": f"ITEM#{counter[0] + i:04d}",
                        "data": f"value_{i}",
                    }
                )

    measure_and_publish("batch_write", do_batch_write, iterations=10)

    # batch_get
    keys = [{"pk": f"{PK_PREFIX}#batch", "sk": f"ITEM#{i:04d}"} for i in range(25)]
    measure_and_publish("batch_get", lambda: client.batch_get(TABLE_NAME, keys), iterations=10)


def run_transaction_benchmarks() -> None:
    """Run transaction operation benchmarks - DISABLED due to parallel conflicts."""
    pass


def run_encryption_benchmarks() -> None:
    """Run encryption benchmarks with KMS."""
    secret_data = "This is sensitive data that needs encryption" * 10
    counter = [0]

    def do_put_encrypted():
        counter[0] += 1
        item = EncryptedItem(
            pk=f"{PK_PREFIX}#encrypted", sk=f"ITEM#{counter[0]:04d}", secret=secret_data
        )
        item.save()

    measure_and_publish("put_encrypted", do_put_encrypted)

    measure_and_publish(
        "get_encrypted",
        lambda: EncryptedItem.get(pk=f"{PK_PREFIX}#encrypted", sk="ITEM#0050"),
    )


def run_compression_benchmarks() -> None:
    """Run compression benchmarks with zstd."""
    large_data = "This is a large piece of data that benefits from compression. " * 100
    counter = [0]

    def do_put_compressed():
        counter[0] += 1
        item = CompressedItem(
            pk=f"{PK_PREFIX}#compressed", sk=f"ITEM#{counter[0]:04d}", data=large_data
        )
        item.save()

    measure_and_publish("put_compressed", do_put_compressed)

    measure_and_publish(
        "get_compressed",
        lambda: CompressedItem.get(pk=f"{PK_PREFIX}#compressed", sk="ITEM#0050"),
    )


def run_s3_benchmarks() -> None:
    """Run S3Attribute benchmarks."""
    large_payload = b"X" * 500_000  # 500KB bytes
    counter = [0]

    def do_put_s3():
        counter[0] += 1
        item = S3Item(pk=f"{PK_PREFIX}#s3", sk=f"ITEM#{counter[0]:04d}")
        item.large_data = S3File(large_payload, name=f"file_{counter[0]}.bin")
        item.save()

    measure_and_publish("put_s3", do_put_s3, iterations=10)

    measure_and_publish(
        "get_s3",
        lambda: S3Item.get(pk=f"{PK_PREFIX}#s3", sk="ITEM#0005"),
        iterations=10,
    )


@metrics.log_metrics(capture_cold_start_metric=True)
@logger.inject_lambda_context
def handler(event: dict, context: LambdaContext) -> dict[str, Any]:
    """Lambda handler that runs pydynox benchmarks."""
    logger.info(f"Starting pydynox benchmarks: memory={MEMORY_SIZE}, arch={ARCHITECTURE}")

    metrics.set_default_dimensions(Memory=MEMORY_SIZE, Architecture=ARCHITECTURE, Library="pydynox")

    run_basic_benchmarks()
    run_batch_benchmarks()
    run_transaction_benchmarks()
    run_encryption_benchmarks()
    run_compression_benchmarks()
    run_s3_benchmarks()

    logger.info("pydynox benchmarks completed")

    return {
        "status": "ok",
        "library": "pydynox",
        "memory": MEMORY_SIZE,
        "architecture": ARCHITECTURE,
    }
