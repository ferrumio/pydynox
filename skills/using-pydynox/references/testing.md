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
`skill_orders` table and runs all workflows, including pagination and transactions. It uses
dummy credentials and unique customer keys for each run.

In a pytest suite, `testcontainers.localstack.LocalStackContainer` can start a
temporary LocalStack instance. Configure `DynamoDBClient` with its endpoint and
test credentials, and set up the table schema before exercising the application.
Docker, `testcontainers`, and `boto3` are development requirements for that setup.

Read the [testing guide](https://ferrumio.github.io/pydynox/guides/testing/) for
fixtures, seeded data, and supported operations.
