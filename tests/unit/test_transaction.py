"""Tests for transaction request tokens and retry behavior."""

from unittest.mock import AsyncMock, MagicMock, call

import pytest
from pydynox import DynamoDBClient, SyncTransaction, Transaction
from pydynox.exceptions import ConnectionException


@pytest.fixture
def client():
    """Create a client that cannot reach AWS."""
    return DynamoDBClient(
        region="us-east-1",
        endpoint_url="http://127.0.0.1:1",
        access_key="testing",
        secret_key="testing",
        max_retries=0,
    )


@pytest.mark.parametrize("sync", [False, True], ids=["async", "sync"])
@pytest.mark.parametrize("context", [False, True], ids=["client", "context"])
@pytest.mark.parametrize(
    "kwargs",
    [
        pytest.param({}, id="omitted"),
        pytest.param({"client_request_token": None}, id="none"),
        pytest.param({"client_request_token": "reserve-order-123"}, id="explicit"),
    ],
)
async def test_transaction_forwards_optional_token(client, sync, context, kwargs):
    # GIVEN a mocked native client and an operation to commit
    native = MagicMock()
    native.transact_write = AsyncMock()
    client._client = native
    item = {"pk": "PRODUCT#123", "stock": 9}
    operations = [{"type": "put", "table": "inventory", "item": item}]

    # WHEN the operation is committed through either public API
    if context:
        if sync:
            with SyncTransaction(client, **kwargs) as tx:
                tx.put("inventory", item)
        else:
            async with Transaction(client, **kwargs) as tx:
                tx.put("inventory", item)
    elif sync:
        assert client.sync_transact_write(operations, **kwargs) is None
    else:
        assert await client.transact_write(operations, **kwargs) is None

    # THEN a missing token preserves the original call without extra arguments
    expected_kwargs = kwargs if kwargs.get("client_request_token") is not None else {}
    if sync:
        native.sync_transact_write.assert_called_once_with(operations, **expected_kwargs)
    else:
        native.transact_write.assert_awaited_once_with(operations, **expected_kwargs)


@pytest.mark.parametrize("sync", [False, True], ids=["async", "sync"])
async def test_failed_commit_keeps_operations_and_token_for_retry(sync):
    # GIVEN a transaction whose first commit has an unknown outcome
    client = MagicMock()
    client.transact_write = AsyncMock(side_effect=[ConnectionException("Timeout"), None])
    client.sync_transact_write.side_effect = [ConnectionException("Timeout"), None]
    transaction = SyncTransaction if sync else Transaction
    tx = transaction(client, client_request_token="reserve-order-123")
    item = {"pk": "PRODUCT#123", "stock": 9}
    tx.put("inventory", item)

    # WHEN the caller retries commit after a connection failure
    with pytest.raises(ConnectionException):
        if sync:
            tx.commit()
        else:
            await tx.commit()
    if sync:
        assert tx.commit() is None
        assert tx.commit() is None
    else:
        assert await tx.commit() is None
        assert await tx.commit() is None

    # THEN both attempts have the same payload and token; the final empty commit is a no-op
    expected = call(
        [{"type": "put", "table": "inventory", "item": item}],
        client_request_token="reserve-order-123",
    )
    calls = (
        client.sync_transact_write.call_args_list if sync else client.transact_write.await_args_list
    )
    assert calls == [expected, expected]


@pytest.mark.parametrize("sync", [False, True], ids=["async", "sync"])
@pytest.mark.parametrize("token", ["", "x" * 37, "é" * 37], ids=["empty", "long", "long-unicode"])
async def test_invalid_token_is_rejected_before_network_request(client, sync, token):
    # GIVEN a nonempty transaction and a token outside DynamoDB's length limits
    operations = [{"type": "put", "table": "inventory", "item": {"pk": "PRODUCT#123"}}]

    # WHEN it is submitted, THEN Rust rejects it before making a network request
    with pytest.raises(ValueError, match="client_request_token must contain between 1 and 36"):
        if sync:
            client.sync_transact_write(operations, client_request_token=token)
        else:
            await client.transact_write(operations, client_request_token=token)


@pytest.mark.parametrize("sync", [False, True], ids=["async", "sync"])
@pytest.mark.parametrize("token", ["x", "x" * 36, "é" * 36, None])
async def test_valid_token_on_empty_transaction_is_noop(client, sync, token):
    # GIVEN an empty transaction with a token at a valid length boundary
    # WHEN it is submitted, THEN no network request is needed
    if sync:
        assert client.sync_transact_write([], client_request_token=token) is None
    else:
        assert await client.transact_write([], client_request_token=token) is None


@pytest.mark.parametrize("transaction", [Transaction, SyncTransaction])
def test_context_token_is_keyword_only(client, transaction):
    with pytest.raises(TypeError):
        transaction(client, "token")


@pytest.mark.parametrize("sync", [False, True], ids=["async", "sync"])
async def test_client_token_is_keyword_only(client, sync):
    with pytest.raises(TypeError):
        if sync:
            client.sync_transact_write([], "token")
        else:
            await client.transact_write([], "token")
