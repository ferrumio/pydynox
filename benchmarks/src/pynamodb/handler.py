"""Benchmark Lambda handler for PynamoDB using Powertools for AWS Lambda."""

from __future__ import annotations

import os
import time
from typing import Any

import boto3
from aws_lambda_powertools import Logger, Metrics
from aws_lambda_powertools.metrics import MetricResolution, MetricUnit
from aws_lambda_powertools.utilities.typing import LambdaContext
from pynamodb.attributes import BinaryAttribute, NumberAttribute, UnicodeAttribute
from pynamodb.models import Model

logger = Logger()
metrics = Metrics()

TABLE_NAME = os.environ["TABLE_NAME"]
BUCKET_NAME = os.environ["BUCKET_NAME"]
KMS_KEY_ID = os.environ["KMS_KEY_ID"]
MEMORY_SIZE = os.environ["MEMORY_SIZE"]
ARCHITECTURE = os.environ["ARCHITECTURE"]

PK_PREFIX = f"PYNAMODB#{MEMORY_SIZE}#{ARCHITECTURE}"

# S3 and KMS clients for advanced benchmarks
s3_client = boto3.client("s3")
kms_client = boto3.client("kms")


class BenchmarkItem(Model):
    class Meta:
        table_name = TABLE_NAME
        region = os.environ.get("AWS_REGION", "us-east-1")

    pk = UnicodeAttribute(hash_key=True)
    sk = UnicodeAttribute(range_key=True)
    data = UnicodeAttribute(default="")
    num = NumberAttribute(default=0)


class EncryptedItem(Model):
    class Meta:
        table_name = TABLE_NAME
        region = os.environ.get("AWS_REGION", "us-east-1")

    pk = UnicodeAttribute(hash_key=True)
    sk = UnicodeAttribute(range_key=True)
    secret = BinaryAttribute(legacy_encoding=False)


class CompressedItem(Model):
    class Meta:
        table_name = TABLE_NAME
        region = os.environ.get("AWS_REGION", "us-east-1")

    pk = UnicodeAttribute(hash_key=True)
    sk = UnicodeAttribute(range_key=True)
    data = BinaryAttribute(legacy_encoding=False)


class S3Item(Model):
    class Meta:
        table_name = TABLE_NAME
        region = os.environ.get("AWS_REGION", "us-east-1")

    pk = UnicodeAttribute(hash_key=True)
    sk = UnicodeAttribute(range_key=True)
    s3_key = UnicodeAttribute()


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
    # Setup
    for i in range(100):
        item = BenchmarkItem(pk=f"{PK_PREFIX}#basic", sk=f"ITEM#{i:04d}", data=f"value_{i}", num=i)
        item.save()

    # put_item
    counter = [0]

    def do_put():
        counter[0] += 1
        item = BenchmarkItem(pk=f"{PK_PREFIX}#put", sk=f"ITEM#{counter[0]:04d}", data="test")
        item.save()

    measure_and_publish("put_item", do_put)

    # get_item
    measure_and_publish("get_item", lambda: BenchmarkItem.get(f"{PK_PREFIX}#basic", "ITEM#0050"))

    # update_item
    def do_update():
        item = BenchmarkItem.get(f"{PK_PREFIX}#basic", "ITEM#0050")
        item.data = "updated"
        item.save()

    measure_and_publish("update_item", do_update)

    # delete_item
    counter[0] = 0

    def do_delete():
        counter[0] += 1
        item = BenchmarkItem.get(f"{PK_PREFIX}#put", f"ITEM#{counter[0]:04d}")
        item.delete()

    measure_and_publish("delete_item", do_delete)

    # query
    measure_and_publish(
        "query",
        lambda: list(BenchmarkItem.query(f"{PK_PREFIX}#basic", limit=10)),
        iterations=10,
    )


def run_batch_benchmarks() -> None:
    """Run batch operation benchmarks."""
    counter = [0]

    def do_batch_write():
        counter[0] += 25
        with BenchmarkItem.batch_write() as batch:
            for i in range(25):
                batch.save(
                    BenchmarkItem(
                        pk=f"{PK_PREFIX}#batch",
                        sk=f"ITEM#{counter[0] + i:04d}",
                        data=f"value_{i}",
                    )
                )

    measure_and_publish("batch_write", do_batch_write, iterations=10)

    # batch_get
    keys = [(f"{PK_PREFIX}#batch", f"ITEM#{i:04d}") for i in range(25)]

    def do_batch_get():
        list(BenchmarkItem.batch_get(keys))

    measure_and_publish("batch_get", do_batch_get, iterations=10)


def run_transaction_benchmarks() -> None:
    """Run transaction operation benchmarks - DISABLED due to parallel conflicts."""
    pass


def run_encryption_benchmarks() -> None:
    """Run encryption benchmarks: PynamoDB + KMS (manual, like boto3)."""
    secret_data = "This is sensitive data that needs encryption" * 10
    counter = [0]

    def do_put_encrypted():
        counter[0] += 1
        encrypted = kms_client.encrypt(KeyId=KMS_KEY_ID, Plaintext=secret_data.encode())
        item = EncryptedItem(
            pk=f"{PK_PREFIX}#encrypted",
            sk=f"ITEM#{counter[0]:04d}",
            secret=encrypted["CiphertextBlob"],
        )
        item.save()

    measure_and_publish("put_encrypted", do_put_encrypted)

    def do_get_encrypted():
        item = EncryptedItem.get(f"{PK_PREFIX}#encrypted", "ITEM#0050")
        if item:
            kms_client.decrypt(CiphertextBlob=item.secret)

    measure_and_publish("get_encrypted", do_get_encrypted)


def run_compression_benchmarks() -> None:
    """Run compression benchmarks: PynamoDB + zstd (manual, like boto3)."""
    import zstandard as zstd

    compressor = zstd.ZstdCompressor()
    decompressor = zstd.ZstdDecompressor()

    large_data = "This is a large piece of data that benefits from compression. " * 100
    counter = [0]

    def do_put_compressed():
        counter[0] += 1
        compressed = compressor.compress(large_data.encode())
        item = CompressedItem(
            pk=f"{PK_PREFIX}#compressed",
            sk=f"ITEM#{counter[0]:04d}",
            data=compressed,
        )
        item.save()

    measure_and_publish("put_compressed", do_put_compressed)

    def do_get_compressed():
        item = CompressedItem.get(f"{PK_PREFIX}#compressed", "ITEM#0050")
        if item:
            decompressor.decompress(item.data)

    measure_and_publish("get_compressed", do_get_compressed)


def run_s3_benchmarks() -> None:
    """Run S3 benchmarks: PynamoDB + S3 (manual, like boto3)."""
    large_payload = "X" * 500_000
    counter = [0]

    def do_put_s3():
        counter[0] += 1
        s3_key = f"bench/{PK_PREFIX}/ITEM_{counter[0]:04d}"
        s3_client.put_object(Bucket=BUCKET_NAME, Key=s3_key, Body=large_payload.encode())
        item = S3Item(pk=f"{PK_PREFIX}#s3", sk=f"ITEM#{counter[0]:04d}", s3_key=s3_key)
        item.save()

    measure_and_publish("put_s3", do_put_s3, iterations=10)

    def do_get_s3():
        item = S3Item.get(f"{PK_PREFIX}#s3", "ITEM#0005")
        if item:
            s3_client.get_object(Bucket=BUCKET_NAME, Key=item.s3_key)

    measure_and_publish("get_s3", do_get_s3, iterations=10)


@metrics.log_metrics(capture_cold_start_metric=True)
@logger.inject_lambda_context
def handler(event: dict, context: LambdaContext) -> dict[str, Any]:
    """Lambda handler that runs PynamoDB benchmarks."""
    logger.info(f"Starting PynamoDB benchmarks: memory={MEMORY_SIZE}, arch={ARCHITECTURE}")

    metrics.set_default_dimensions(
        Memory=MEMORY_SIZE, Architecture=ARCHITECTURE, Library="pynamodb"
    )

    run_basic_benchmarks()
    run_batch_benchmarks()
    run_transaction_benchmarks()
    run_encryption_benchmarks()
    run_compression_benchmarks()
    run_s3_benchmarks()

    logger.info("PynamoDB benchmarks completed")

    return {
        "status": "ok",
        "library": "pynamodb",
        "memory": MEMORY_SIZE,
        "architecture": ARCHITECTURE,
    }
