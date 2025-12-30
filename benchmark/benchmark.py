"""
Benchmark suite comparing pydynox vs PynamoDB vs boto3.

Run with: uv run pytest bench/benchmark.py -v --benchmark-only
"""

import uuid

import pytest

TABLE_NAME = "bench_table"


# =============================================================================
# PUT ITEM BENCHMARKS (10 operations)
# =============================================================================


def test_pydynox_put_item_10x(benchmark, pydynox_client):
    """Benchmark pydynox put_item - 10 operations."""

    def put_items():
        for _ in range(10):
            item = {
                "pk": f"USER#{uuid.uuid4()}",
                "sk": "PROFILE",
                "name": "John Doe",
                "age": 30,
                "email": "john@example.com",
                "status": "active",
            }
            pydynox_client.put_item(TABLE_NAME, item)

    benchmark(put_items)


def test_pynamodb_put_item_10x(benchmark, pynamodb_model):
    """Benchmark PynamoDB save - 10 operations."""

    def put_items():
        for _ in range(10):
            item = pynamodb_model(
                pk=f"USER#{uuid.uuid4()}",
                sk="PROFILE",
                name="John Doe",
                age=30,
                email="john@example.com",
                status="active",
            )
            item.save()

    benchmark(put_items)


def test_boto3_put_item_10x(benchmark, boto_client):
    """Benchmark boto3 put_item - 10 operations."""

    def put_items():
        for _ in range(10):
            boto_client.put_item(
                TableName=TABLE_NAME,
                Item={
                    "pk": {"S": f"USER#{uuid.uuid4()}"},
                    "sk": {"S": "PROFILE"},
                    "name": {"S": "John Doe"},
                    "age": {"N": "30"},
                    "email": {"S": "john@example.com"},
                    "status": {"S": "active"},
                },
            )

    benchmark(put_items)


# =============================================================================
# GET ITEM BENCHMARKS (10 operations)
# =============================================================================


@pytest.fixture(scope="session")
def pydynox_get_keys(pydynox_client):
    """Create 10 items for pydynox get benchmark."""
    keys = []
    for _ in range(10):
        key = f"GET_PYDYNOX#{uuid.uuid4()}"
        pydynox_client.put_item(
            TABLE_NAME,
            {
                "pk": key,
                "sk": "PROFILE",
                "name": "Test User",
                "age": 25,
                "email": "test@example.com",
                "status": "active",
            },
        )
        keys.append(key)
    return keys


@pytest.fixture(scope="session")
def pynamodb_get_keys(pydynox_client):
    """Create 10 items for PynamoDB get benchmark."""
    keys = []
    for _ in range(10):
        key = f"GET_PYNAMODB#{uuid.uuid4()}"
        pydynox_client.put_item(
            TABLE_NAME,
            {
                "pk": key,
                "sk": "PROFILE",
                "name": "Test User",
                "age": 25,
                "email": "test@example.com",
                "status": "active",
            },
        )
        keys.append(key)
    return keys


@pytest.fixture(scope="session")
def boto3_get_keys(pydynox_client):
    """Create 10 items for boto3 get benchmark."""
    keys = []
    for _ in range(10):
        key = f"GET_BOTO3#{uuid.uuid4()}"
        pydynox_client.put_item(
            TABLE_NAME,
            {
                "pk": key,
                "sk": "PROFILE",
                "name": "Test User",
                "age": 25,
                "email": "test@example.com",
                "status": "active",
            },
        )
        keys.append(key)
    return keys


def test_pydynox_get_item_10x(benchmark, pydynox_client, pydynox_get_keys):
    """Benchmark pydynox get_item - 10 operations."""

    def get_items():
        for key in pydynox_get_keys:
            pydynox_client.get_item(TABLE_NAME, {"pk": key, "sk": "PROFILE"})

    benchmark(get_items)


def test_pynamodb_get_item_10x(benchmark, pynamodb_model, pynamodb_get_keys):
    """Benchmark PynamoDB get - 10 operations."""

    def get_items():
        for key in pynamodb_get_keys:
            pynamodb_model.get(key, "PROFILE")

    benchmark(get_items)


def test_boto3_get_item_10x(benchmark, boto_client, boto3_get_keys):
    """Benchmark boto3 get_item - 10 operations."""

    def get_items():
        for key in boto3_get_keys:
            boto_client.get_item(
                TableName=TABLE_NAME,
                Key={"pk": {"S": key}, "sk": {"S": "PROFILE"}},
            )

    benchmark(get_items)


# =============================================================================
# QUERY BENCHMARKS (100 items)
# =============================================================================


@pytest.fixture(scope="session")
def pydynox_query_pk(pydynox_client):
    """Create items for pydynox query benchmark."""
    pk = f"QUERY_PYDYNOX#{uuid.uuid4()}"
    for i in range(100):
        pydynox_client.put_item(
            TABLE_NAME,
            {
                "pk": pk,
                "sk": f"ITEM#{i:04d}",
                "name": f"Item {i}",
                "age": i,
                "status": "active" if i % 2 == 0 else "inactive",
            },
        )
    return pk


@pytest.fixture(scope="session")
def pynamodb_query_pk(pydynox_client):
    """Create items for PynamoDB query benchmark."""
    pk = f"QUERY_PYNAMODB#{uuid.uuid4()}"
    for i in range(100):
        pydynox_client.put_item(
            TABLE_NAME,
            {
                "pk": pk,
                "sk": f"ITEM#{i:04d}",
                "name": f"Item {i}",
                "age": i,
                "status": "active" if i % 2 == 0 else "inactive",
            },
        )
    return pk


@pytest.fixture(scope="session")
def boto3_query_pk(pydynox_client):
    """Create items for boto3 query benchmark."""
    pk = f"QUERY_BOTO3#{uuid.uuid4()}"
    for i in range(100):
        pydynox_client.put_item(
            TABLE_NAME,
            {
                "pk": pk,
                "sk": f"ITEM#{i:04d}",
                "name": f"Item {i}",
                "age": i,
                "status": "active" if i % 2 == 0 else "inactive",
            },
        )
    return pk


def test_pydynox_query(benchmark, pydynox_client, pydynox_query_pk):
    """Benchmark pydynox query - 100 items."""

    def query():
        items = []
        for item in pydynox_client.query(
            TABLE_NAME,
            key_condition_expression="pk = :pk",
            expression_attribute_values={":pk": pydynox_query_pk},
        ):
            items.append(item)
        return items

    result = benchmark(query)
    assert len(result) == 100


def test_pynamodb_query(benchmark, pynamodb_model, pynamodb_query_pk):
    """Benchmark PynamoDB query - 100 items."""

    def query():
        return list(pynamodb_model.query(pynamodb_query_pk))

    result = benchmark(query)
    assert len(result) == 100


def test_boto3_query(benchmark, boto_client, boto3_query_pk):
    """Benchmark boto3 query - 100 items."""

    def query():
        response = boto_client.query(
            TableName=TABLE_NAME,
            KeyConditionExpression="pk = :pk",
            ExpressionAttributeValues={":pk": {"S": boto3_query_pk}},
        )
        return response["Items"]

    result = benchmark(query)
    assert len(result) == 100


# =============================================================================
# UPDATE ITEM BENCHMARKS (10 operations)
# =============================================================================


@pytest.fixture(scope="session")
def pydynox_update_keys(pydynox_client):
    """Create 10 items for pydynox update benchmark."""
    keys = []
    for _ in range(10):
        key = f"UPDATE_PYDYNOX#{uuid.uuid4()}"
        pydynox_client.put_item(
            TABLE_NAME,
            {
                "pk": key,
                "sk": "PROFILE",
                "name": "Original Name",
                "age": 20,
                "status": "pending",
            },
        )
        keys.append(key)
    return keys


@pytest.fixture(scope="session")
def pynamodb_update_keys(pydynox_client):
    """Create 10 items for PynamoDB update benchmark."""
    keys = []
    for _ in range(10):
        key = f"UPDATE_PYNAMODB#{uuid.uuid4()}"
        pydynox_client.put_item(
            TABLE_NAME,
            {
                "pk": key,
                "sk": "PROFILE",
                "name": "Original Name",
                "age": 20,
                "status": "pending",
            },
        )
        keys.append(key)
    return keys


@pytest.fixture(scope="session")
def boto3_update_keys(pydynox_client):
    """Create 10 items for boto3 update benchmark."""
    keys = []
    for _ in range(10):
        key = f"UPDATE_BOTO3#{uuid.uuid4()}"
        pydynox_client.put_item(
            TABLE_NAME,
            {
                "pk": key,
                "sk": "PROFILE",
                "name": "Original Name",
                "age": 20,
                "status": "pending",
            },
        )
        keys.append(key)
    return keys


def test_pydynox_update_item_10x(benchmark, pydynox_client, pydynox_update_keys):
    """Benchmark pydynox update_item - 10 operations."""
    counter = [0]

    def update_items():
        counter[0] += 1
        for key in pydynox_update_keys:
            pydynox_client.update_item(
                TABLE_NAME,
                {"pk": key, "sk": "PROFILE"},
                update_expression="SET #name = :name, age = :age",
                expression_attribute_names={"#name": "name"},
                expression_attribute_values={":name": f"Updated {counter[0]}", ":age": counter[0]},
            )

    benchmark(update_items)


def test_pynamodb_update_item_10x(benchmark, pynamodb_model, pynamodb_update_keys):
    """Benchmark PynamoDB update - 10 operations."""
    counter = [0]

    def update_items():
        counter[0] += 1
        for key in pynamodb_update_keys:
            item = pynamodb_model.get(key, "PROFILE")
            item.update(
                actions=[
                    pynamodb_model.name.set(f"Updated {counter[0]}"),
                    pynamodb_model.age.set(counter[0]),
                ]
            )

    benchmark(update_items)


def test_boto3_update_item_10x(benchmark, boto_client, boto3_update_keys):
    """Benchmark boto3 update_item - 10 operations."""
    counter = [0]

    def update_items():
        counter[0] += 1
        for key in boto3_update_keys:
            boto_client.update_item(
                TableName=TABLE_NAME,
                Key={"pk": {"S": key}, "sk": {"S": "PROFILE"}},
                UpdateExpression="SET #name = :name, age = :age",
                ExpressionAttributeNames={"#name": "name"},
                ExpressionAttributeValues={
                    ":name": {"S": f"Updated {counter[0]}"},
                    ":age": {"N": str(counter[0])},
                },
            )

    benchmark(update_items)


# =============================================================================
# DELETE ITEM BENCHMARKS (10 operations)
# =============================================================================


def test_pydynox_delete_item_10x(benchmark, pydynox_client):
    """Benchmark pydynox delete_item - 10 operations."""

    def delete_items():
        for _ in range(10):
            key = f"DELETE_TEST#{uuid.uuid4()}"
            pydynox_client.put_item(
                TABLE_NAME,
                {"pk": key, "sk": "PROFILE", "name": "To Delete"},
            )
            pydynox_client.delete_item(TABLE_NAME, {"pk": key, "sk": "PROFILE"})

    benchmark(delete_items)


def test_pynamodb_delete_item_10x(benchmark, pynamodb_model):
    """Benchmark PynamoDB delete - 10 operations."""

    def delete_items():
        for _ in range(10):
            key = f"DELETE_TEST#{uuid.uuid4()}"
            item = pynamodb_model(pk=key, sk="PROFILE", name="To Delete")
            item.save()
            item.delete()

    benchmark(delete_items)


def test_boto3_delete_item_10x(benchmark, boto_client):
    """Benchmark boto3 delete_item - 10 operations."""

    def delete_items():
        for _ in range(10):
            key = f"DELETE_TEST#{uuid.uuid4()}"
            boto_client.put_item(
                TableName=TABLE_NAME,
                Item={
                    "pk": {"S": key},
                    "sk": {"S": "PROFILE"},
                    "name": {"S": "To Delete"},
                },
            )
            boto_client.delete_item(
                TableName=TABLE_NAME,
                Key={"pk": {"S": key}, "sk": {"S": "PROFILE"}},
            )

    benchmark(delete_items)


# =============================================================================
# BATCH WRITE BENCHMARKS (100 items)
# =============================================================================


def test_pydynox_batch_write_100(benchmark, pydynox_client):
    """Benchmark pydynox batch_write - 100 items."""
    counter = [0]

    def batch_write():
        counter[0] += 1
        items = [
            {
                "pk": f"BATCH_WRITE_PYDYNOX#{counter[0]}",
                "sk": f"ITEM#{i:04d}",
                "name": f"Item {i}",
                "age": i,
            }
            for i in range(100)
        ]
        pydynox_client.batch_write(TABLE_NAME, put_items=items)

    benchmark(batch_write)


def test_pynamodb_batch_write_100(benchmark, pynamodb_model):
    """Benchmark PynamoDB batch_write - 100 items."""
    counter = [0]

    def batch_write():
        counter[0] += 1
        with pynamodb_model.batch_write() as batch:
            for i in range(100):
                item = pynamodb_model(
                    pk=f"BATCH_WRITE_PYNAMODB#{counter[0]}",
                    sk=f"ITEM#{i:04d}",
                    name=f"Item {i}",
                    age=i,
                )
                batch.save(item)

    benchmark(batch_write)


def test_boto3_batch_write_100(benchmark, boto_client):
    """Benchmark boto3 batch_write - 100 items."""
    counter = [0]

    def batch_write():
        counter[0] += 1
        # boto3 batch_write_item has 25-item limit, so we need multiple calls
        items = [
            {
                "PutRequest": {
                    "Item": {
                        "pk": {"S": f"BATCH_WRITE_BOTO3#{counter[0]}"},
                        "sk": {"S": f"ITEM#{i:04d}"},
                        "name": {"S": f"Item {i}"},
                        "age": {"N": str(i)},
                    }
                }
            }
            for i in range(100)
        ]
        # Split into chunks of 25
        for chunk_start in range(0, 100, 25):
            chunk = items[chunk_start : chunk_start + 25]
            boto_client.batch_write_item(RequestItems={TABLE_NAME: chunk})

    benchmark(batch_write)


# =============================================================================
# BATCH GET BENCHMARKS (100 items)
# =============================================================================


@pytest.fixture(scope="session")
def pydynox_batch_get_keys(pydynox_client):
    """Create 100 items for pydynox batch_get benchmark."""
    pk = f"BATCH_GET_PYDYNOX#{uuid.uuid4()}"
    keys = []
    items = []
    for i in range(100):
        sk = f"ITEM#{i:04d}"
        items.append({"pk": pk, "sk": sk, "name": f"Item {i}", "age": i})
        keys.append({"pk": pk, "sk": sk})
    pydynox_client.batch_write(TABLE_NAME, put_items=items)
    return keys


@pytest.fixture(scope="session")
def pynamodb_batch_get_keys(pydynox_client):
    """Create 100 items for PynamoDB batch_get benchmark."""
    pk = f"BATCH_GET_PYNAMODB#{uuid.uuid4()}"
    keys = []
    items = []
    for i in range(100):
        sk = f"ITEM#{i:04d}"
        items.append({"pk": pk, "sk": sk, "name": f"Item {i}", "age": i})
        keys.append((pk, sk))
    pydynox_client.batch_write(TABLE_NAME, put_items=items)
    return keys


@pytest.fixture(scope="session")
def boto3_batch_get_keys(pydynox_client):
    """Create 100 items for boto3 batch_get benchmark."""
    pk = f"BATCH_GET_BOTO3#{uuid.uuid4()}"
    keys = []
    items = []
    for i in range(100):
        sk = f"ITEM#{i:04d}"
        items.append({"pk": pk, "sk": sk, "name": f"Item {i}", "age": i})
        keys.append({"pk": {"S": pk}, "sk": {"S": sk}})
    pydynox_client.batch_write(TABLE_NAME, put_items=items)
    return keys


def test_pydynox_batch_get_100(benchmark, pydynox_client, pydynox_batch_get_keys):
    """Benchmark pydynox batch_get - 100 items."""

    def batch_get():
        return pydynox_client.batch_get(TABLE_NAME, pydynox_batch_get_keys)

    result = benchmark(batch_get)
    assert len(result) == 100


def test_pynamodb_batch_get_100(benchmark, pynamodb_model, pynamodb_batch_get_keys):
    """Benchmark PynamoDB batch_get - 100 items."""

    def batch_get():
        return list(pynamodb_model.batch_get(pynamodb_batch_get_keys))

    result = benchmark(batch_get)
    assert len(result) == 100


def test_boto3_batch_get_100(benchmark, boto_client, boto3_batch_get_keys):
    """Benchmark boto3 batch_get - 100 items."""

    def batch_get():
        # boto3 batch_get_item has 100-item limit
        response = boto_client.batch_get_item(
            RequestItems={TABLE_NAME: {"Keys": boto3_batch_get_keys}}
        )
        return response["Responses"][TABLE_NAME]

    result = benchmark(batch_get)
    assert len(result) == 100


# =============================================================================
# TRANSACTION WRITE BENCHMARKS (10 items)
# Note: Transaction benchmarks are skipped because moto's transact_write
# implementation is slow/unstable. The functionality is tested in
# tests/integration/operations/test_transaction.py
# =============================================================================
