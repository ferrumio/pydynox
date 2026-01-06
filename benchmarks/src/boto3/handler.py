"""Benchmark Lambda handler for boto3 using Powertools for AWS Lambda."""

from __future__ import annotations

import os
import time
from typing import Any

import boto3
import zstandard as zstd
from aws_lambda_powertools import Logger, Metrics
from aws_lambda_powertools.metrics import MetricResolution, MetricUnit
from aws_lambda_powertools.utilities.typing import LambdaContext

logger = Logger()
metrics = Metrics()

TABLE_NAME = os.environ["TABLE_NAME"]
BUCKET_NAME = os.environ["BUCKET_NAME"]
KMS_KEY_ID = os.environ["KMS_KEY_ID"]
MEMORY_SIZE = os.environ["MEMORY_SIZE"]
ARCHITECTURE = os.environ["ARCHITECTURE"]

# Unique prefix per Lambda config to avoid conflicts when running in parallel
PK_PREFIX = f"BOTO3#{MEMORY_SIZE}#{ARCHITECTURE}"

# Initialize clients at module level (cold start)
dynamodb = boto3.client("dynamodb")
s3_client = boto3.client("s3")
kms_client = boto3.client("kms")
compressor = zstd.ZstdCompressor()
decompressor = zstd.ZstdDecompressor()


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


def put_item(pk: str, sk: str, data: dict) -> None:
    item = {"pk": {"S": pk}, "sk": {"S": sk}}
    for k, v in data.items():
        if isinstance(v, str):
            item[k] = {"S": v}
        elif isinstance(v, (int, float)):
            item[k] = {"N": str(v)}
    dynamodb.put_item(TableName=TABLE_NAME, Item=item)


def get_item(pk: str, sk: str) -> dict | None:
    response = dynamodb.get_item(TableName=TABLE_NAME, Key={"pk": {"S": pk}, "sk": {"S": sk}})
    return response.get("Item")


def update_item(pk: str, sk: str, data: dict) -> None:
    update_expr = "SET " + ", ".join(f"#{k} = :{k}" for k in data.keys())
    expr_names = {f"#{k}": k for k in data.keys()}
    expr_values = {}
    for k, v in data.items():
        if isinstance(v, str):
            expr_values[f":{k}"] = {"S": v}
        elif isinstance(v, (int, float)):
            expr_values[f":{k}"] = {"N": str(v)}

    dynamodb.update_item(
        TableName=TABLE_NAME,
        Key={"pk": {"S": pk}, "sk": {"S": sk}},
        UpdateExpression=update_expr,
        ExpressionAttributeNames=expr_names,
        ExpressionAttributeValues=expr_values,
    )


def delete_item(pk: str, sk: str) -> None:
    dynamodb.delete_item(TableName=TABLE_NAME, Key={"pk": {"S": pk}, "sk": {"S": sk}})


def query(pk: str, limit: int = 10) -> list:
    response = dynamodb.query(
        TableName=TABLE_NAME,
        KeyConditionExpression="pk = :pk",
        ExpressionAttributeValues={":pk": {"S": pk}},
        Limit=limit,
    )
    # Deserialize to dicts like pydynox does
    items = []
    for item in response.get("Items", []):
        obj = {}
        for k, v in item.items():
            if "S" in v:
                obj[k] = v["S"]
            elif "N" in v:
                obj[k] = float(v["N"]) if "." in v["N"] else int(v["N"])
            elif "B" in v:
                obj[k] = v["B"]
        items.append(obj)
    return items


def batch_write(items: list[dict]) -> None:
    request_items = []
    for item in items:
        dynamo_item = {}
        for k, v in item.items():
            if isinstance(v, str):
                dynamo_item[k] = {"S": v}
            elif isinstance(v, (int, float)):
                dynamo_item[k] = {"N": str(v)}
        request_items.append({"PutRequest": {"Item": dynamo_item}})

    dynamodb.batch_write_item(RequestItems={TABLE_NAME: request_items})


def batch_get(keys: list[dict]) -> list:
    dynamo_keys = [{"pk": {"S": k["pk"]}, "sk": {"S": k["sk"]}} for k in keys]
    response = dynamodb.batch_get_item(RequestItems={TABLE_NAME: {"Keys": dynamo_keys}})
    return response.get("Responses", {}).get(TABLE_NAME, [])


def transact_write(items: list[dict]) -> None:
    transact_items = []
    for item in items:
        dynamo_item = {}
        for k, v in item.items():
            if isinstance(v, str):
                dynamo_item[k] = {"S": v}
            elif isinstance(v, (int, float)):
                dynamo_item[k] = {"N": str(v)}
        transact_items.append({"Put": {"TableName": TABLE_NAME, "Item": dynamo_item}})

    dynamodb.transact_write_items(TransactItems=transact_items)


def transact_get(keys: list[dict]) -> list:
    transact_items = [
        {"Get": {"TableName": TABLE_NAME, "Key": {"pk": {"S": k["pk"]}, "sk": {"S": k["sk"]}}}}
        for k in keys
    ]
    response = dynamodb.transact_get_items(TransactItems=transact_items)
    return [r.get("Item") for r in response.get("Responses", [])]


def run_basic_benchmarks() -> None:
    """Run basic operation benchmarks."""
    # Setup
    for i in range(100):
        put_item(f"{PK_PREFIX}#basic", f"ITEM#{i:04d}", {"data": f"value_{i}", "num": i})

    # put_item
    counter = [0]

    def do_put():
        counter[0] += 1
        put_item(f"{PK_PREFIX}#put", f"ITEM#{counter[0]:04d}", {"data": "test"})

    measure_and_publish("put_item", do_put)

    # get_item
    measure_and_publish("get_item", lambda: get_item(f"{PK_PREFIX}#basic", "ITEM#0050"))

    # update_item
    def do_update():
        item = get_item(f"{PK_PREFIX}#basic", "ITEM#0050")
        if item:
            update_item(f"{PK_PREFIX}#basic", "ITEM#0050", {"data": "updated"})

    measure_and_publish("update_item", do_update)

    # delete_item
    counter[0] = 0

    def do_delete():
        counter[0] += 1
        item = get_item(f"{PK_PREFIX}#put", f"ITEM#{counter[0]:04d}")
        if item:
            delete_item(f"{PK_PREFIX}#put", f"ITEM#{counter[0]:04d}")

    measure_and_publish("delete_item", do_delete)

    # query
    measure_and_publish("query", lambda: query(f"{PK_PREFIX}#basic", limit=10), iterations=10)


def run_batch_benchmarks() -> None:
    """Run batch operation benchmarks."""
    counter = [0]

    def do_batch_write():
        counter[0] += 25
        items = [
            {"pk": f"{PK_PREFIX}#batch", "sk": f"ITEM#{counter[0] + i:04d}", "data": f"value_{i}"}
            for i in range(25)
        ]
        batch_write(items)

    measure_and_publish("batch_write", do_batch_write, iterations=10)

    keys = [{"pk": f"{PK_PREFIX}#batch", "sk": f"ITEM#{i:04d}"} for i in range(25)]
    measure_and_publish("batch_get", lambda: batch_get(keys), iterations=10)


def run_transaction_benchmarks() -> None:
    """Run transaction operation benchmarks - DISABLED due to parallel conflicts."""
    pass


def run_encryption_benchmarks() -> None:
    """Run encryption benchmarks: boto3 + KMS."""
    secret_data = "This is sensitive data that needs encryption" * 10
    counter = [0]

    def do_put_encrypted():
        counter[0] += 1
        encrypted = kms_client.encrypt(KeyId=KMS_KEY_ID, Plaintext=secret_data.encode())
        dynamodb.put_item(
            TableName=TABLE_NAME,
            Item={
                "pk": {"S": f"{PK_PREFIX}#encrypted"},
                "sk": {"S": f"ITEM#{counter[0]:04d}"},
                "secret": {"B": encrypted["CiphertextBlob"]},
            },
        )

    measure_and_publish("put_encrypted", do_put_encrypted)

    def do_get_encrypted():
        response = dynamodb.get_item(
            TableName=TABLE_NAME,
            Key={"pk": {"S": f"{PK_PREFIX}#encrypted"}, "sk": {"S": "ITEM#0050"}},
        )
        if item := response.get("Item"):
            kms_client.decrypt(CiphertextBlob=item["secret"]["B"])

    measure_and_publish("get_encrypted", do_get_encrypted)


def run_compression_benchmarks() -> None:
    """Run compression benchmarks: boto3 + python zstd."""
    large_data = "This is a large piece of data that benefits from compression. " * 100
    counter = [0]

    def do_put_compressed():
        counter[0] += 1
        compressed = compressor.compress(large_data.encode())
        dynamodb.put_item(
            TableName=TABLE_NAME,
            Item={
                "pk": {"S": f"{PK_PREFIX}#compressed"},
                "sk": {"S": f"ITEM#{counter[0]:04d}"},
                "data": {"B": compressed},
            },
        )

    measure_and_publish("put_compressed", do_put_compressed)

    def do_get_compressed():
        response = dynamodb.get_item(
            TableName=TABLE_NAME,
            Key={"pk": {"S": f"{PK_PREFIX}#compressed"}, "sk": {"S": "ITEM#0050"}},
        )
        if item := response.get("Item"):
            decompressor.decompress(item["data"]["B"])

    measure_and_publish("get_compressed", do_get_compressed)


def run_s3_benchmarks() -> None:
    """Run S3 benchmarks: boto3 DynamoDB + S3."""
    large_payload = "X" * 500_000  # 500KB
    counter = [0]

    def do_put_s3():
        counter[0] += 1
        s3_key = f"bench/{PK_PREFIX}/ITEM_{counter[0]:04d}"
        s3_client.put_object(Bucket=BUCKET_NAME, Key=s3_key, Body=large_payload.encode())
        dynamodb.put_item(
            TableName=TABLE_NAME,
            Item={
                "pk": {"S": f"{PK_PREFIX}#s3"},
                "sk": {"S": f"ITEM#{counter[0]:04d}"},
                "s3_key": {"S": s3_key},
            },
        )

    measure_and_publish("put_s3", do_put_s3, iterations=10)

    def do_get_s3():
        response = dynamodb.get_item(
            TableName=TABLE_NAME,
            Key={"pk": {"S": f"{PK_PREFIX}#s3"}, "sk": {"S": "ITEM#0005"}},
        )
        if item := response.get("Item"):
            s3_client.get_object(Bucket=BUCKET_NAME, Key=item["s3_key"]["S"])

    measure_and_publish("get_s3", do_get_s3, iterations=10)


@metrics.log_metrics(capture_cold_start_metric=True)
@logger.inject_lambda_context
def handler(event: dict, context: LambdaContext) -> dict[str, Any]:
    """Lambda handler that runs boto3 benchmarks."""
    logger.info(f"Starting boto3 benchmarks: memory={MEMORY_SIZE}, arch={ARCHITECTURE}")

    metrics.set_default_dimensions(Memory=MEMORY_SIZE, Architecture=ARCHITECTURE, Library="boto3")

    run_basic_benchmarks()
    run_batch_benchmarks()
    run_transaction_benchmarks()
    run_encryption_benchmarks()
    run_compression_benchmarks()
    run_s3_benchmarks()

    logger.info("boto3 benchmarks completed")

    return {"status": "ok", "library": "boto3", "memory": MEMORY_SIZE, "architecture": ARCHITECTURE}
