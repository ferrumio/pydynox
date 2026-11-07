# Testing applications

The [application example](../examples/application.py) runs without AWS:

```bash
python path/to/using-pydynox/examples/application.py
```

Its default entrypoint keeps a `MemoryBackend` context active while the async
and sync CRUD, query, and batch workflows run. Each workflow contains assertions
about the data read back.

## Memory tests

Install `pytest` and `pytest-asyncio` as application development dependencies.
The installed pydynox package registers a `pydynox_memory_backend` pytest fixture.
Add that fixture to a test using models with the default client.

The fixture replaces the default client for the duration of the test. For direct
client calls, use `pydynox_memory_backend.client`. A model with an explicit
`ModelConfig(client=...)` continues using that client, so use an appropriate
test client for it.

Without pytest, use `with MemoryBackend():` around the operations. In async code,
keep that context open until the awaited work finishes.

The memory backend is useful for CRUD, conditions, queries, and batch operations.
It does not provide continuation keys. Use LocalStack for pagination,
transactions, GSI behavior, and checks that need the actual SDK transport.
Memory tests do not verify AWS credentials, IAM, or service limits.

## LocalStack

The bundled example also accepts a LocalStack endpoint:

```bash
python path/to/using-pydynox/examples/application.py \
  --endpoint-url http://localhost:4566
```

Start LocalStack with DynamoDB first. This mode creates the example's
`skill_orders` table and runs all workflows, including pagination and transactions.
It uses dummy credentials and unique customer keys for each run.

For streaming, "load more", empty filtered pages, descending order, projections,
GSI cursors, and scans, run [query_patterns.py](../examples/query_patterns.py):

```bash
python path/to/using-pydynox/examples/query_patterns.py \
  --endpoint-url http://localhost:4566
```

It creates `skill_query_orders` with a GSI and runs both async and sync recipes.
The empty filtered-page recipes require the fix merged after pydynox 1.8.0.
The CLI's table creation is local example setup; application tests can instead
provide a client and provision the schema in fixtures.

In a pytest suite, `testcontainers.localstack.LocalStackContainer` can start a
temporary LocalStack instance. Configure `DynamoDBClient` with its endpoint and
test credentials, and set up the table schema before exercising the application.
Docker, `testcontainers`, and `boto3` are development requirements for that setup.

Read the [testing guide](https://ferrumio.github.io/pydynox/guides/testing/) for
fixtures, seeded data, and supported operations.

## Assert the application's contract

| Feature | Assertions that catch mistakes |
|---------|-------------------------------|
| Create-only write | Duplicate key is rejected and original data remains |
| State transition | A stale condition fails without changing the stored state |
| Atomic update | Read back the expected stored increment |
| Cursor pagination | Follow every cursor; no missing or duplicate keys; preserve order |
| Filtered pagination | Empty service pages do not hide later matches |
| Projection | Returned fields and types match the endpoint's contract |
| GSI | Wait with a deadline for seed visibility, then check keys and cursor shape |
| Transaction | A rejected condition leaves the other proposed write absent |

Keep keys unique between tests and keep the fixture's client active until
awaited operations finish. Test async and sync entrypoints used by the
application. For expiry, S3, KMS, or hooks, use the linked feature guide to
identify what the chosen backend actually simulates.
