"""Exercise exact decimals through native DynamoDB requests and model APIs."""

import asyncio
from decimal import Decimal, localcontext
from uuid import uuid4

import pytest
from pydynox import Model, ModelConfig
from pydynox.attributes import DecimalAttribute, NumberAttribute, StringAttribute
from pydynox.exceptions import ConditionalCheckFailedException
from pydynox.indexes import GlobalSecondaryIndex, LocalSecondaryIndex
from pydynox.transaction import SyncTransaction, Transaction

EXACT = Decimal("12345678901234567890.123456789012345678")


@pytest.fixture
def account_model(dynamo):
    class Account(Model):
        model_config = ModelConfig(table="test_table", client=dynamo)
        pk = StringAttribute(partition_key=True)
        sk = StringAttribute(sort_key=True)
        balance = DecimalAttribute(alias="b")
        count = NumberAttribute()
        ratio = NumberAttribute()

    return Account


@pytest.mark.parametrize("mode", ["sync", "async"])
async def test_model_reads_updates_batches_and_transactions(account_model, dynamo, mode):
    # GIVEN a model with more fractional digits than float can represent
    Account = account_model
    pk = f"decimal-{uuid4()}"
    account = Account(pk=pk, sk="1", balance=EXACT, count=7, ratio=0.25)
    with localcontext() as context:
        context.prec = 6
        # WHEN saving with the requested API
        if mode == "sync":
            account.sync_save()
            loaded = Account.sync_get(pk=pk, sk="1")
        else:
            await account.save()
            loaded = await Account.get(pk=pk, sk="1")
        # THEN decoding is independent of the arithmetic context
        assert loaded.balance == EXACT
        assert type(loaded.balance) is Decimal
        assert type(loaded.count) is int
        assert type(loaded.ratio) is float
        assert not loaded.is_dirty

        # WHEN updating through a Decimal condition and an atomic increment
        kwargs = {
            "atomic": [Account.balance.add(Decimal("0.000000000000000001"))],
            "condition": Account.balance == EXACT,
        }
        if mode == "sync":
            loaded.sync_update(**kwargs)
        else:
            await loaded.update(**kwargs)
        expected = Decimal("12345678901234567890.123456789012345679")

        # WHEN reading via paginated queries, scans, batches, PartiQL, and parallel scan
        keys = [{"pk": pk, "sk": "1"}]
        if mode == "sync":
            batches = Account.sync_batch_get(keys)
            query = list(Account.sync_query(pk, page_size=1))
            scan = list(Account.sync_scan(filter_condition=Account.pk == pk, page_size=2))
            statement = Account.sync_execute_statement(
                'SELECT * FROM "test_table" WHERE pk=?', [pk]
            )
            parallel, _ = Account.sync_parallel_scan(2, filter_condition=Account.pk == pk)
            raw = Account.sync_get(pk=pk, sk="1", as_dict=True)
        else:
            batches = await Account.batch_get(keys)
            query = [item async for item in Account.query(pk, page_size=1)]
            scan = [
                item async for item in Account.scan(filter_condition=Account.pk == pk, page_size=2)
            ]
            statement = await Account.execute_statement(
                'SELECT * FROM "test_table" WHERE pk=?', [pk]
            )
            parallel, _ = await Account.parallel_scan(2, filter_condition=Account.pk == pk)
            raw = await Account.get(pk=pk, sk="1", as_dict=True)
        # THEN each read path retains the original decimal text
        for results in (batches, query, scan, statement, parallel):
            assert len(results) == 1
            assert results[0].balance == expected
        assert raw["b"] == expected

        # WHEN writing a model in a transaction and reading an atomic snapshot
        second = Account(pk=pk, sk="2", balance=EXACT)
        gets = [
            {"table": "test_table", "key": {"pk": pk, "sk": "2"}},
            {"table": "test_table", "key": {"pk": pk, "sk": "missing"}},
        ]
        if mode == "sync":
            with SyncTransaction(dynamo) as txn:
                txn.save_model(second)
            snapshot = dynamo.sync_transact_get(gets)
            dynamo.sync_batch_write("test_table", put_items=[{"pk": pk, "sk": "3", "b": EXACT}])
            raw_batch = dynamo.sync_batch_get("test_table", [{"pk": pk, "sk": "3"}])
        else:
            async with Transaction(dynamo) as txn:
                txn.save_model(second)
            snapshot = await dynamo.transact_get(gets)
            await dynamo.batch_write("test_table", put_items=[{"pk": pk, "sk": "3", "b": EXACT}])
            raw_batch = await dynamo.batch_get("test_table", [{"pk": pk, "sk": "3"}])
        assert type(snapshot[0]["b"]) is float
        assert snapshot[1] is None
        assert type(raw_batch[0]["b"]) is float
        # A model read of the same transaction/batch writes is exact automatically.
        written = Account.sync_batch_get([{"pk": pk, "sk": "2"}, {"pk": pk, "sk": "3"}])
        assert len(written) == 2
        assert all(item.balance == EXACT for item in written)
        assert context.prec == 6

    # THEN the default raw API still returns floats
    ordinary = dynamo.sync_get_item("test_table", {"pk": pk, "sk": "1"})
    assert type(ordinary["b"]) is float
    # Clean up so later scans in the full suite do not inherit these records.
    dynamo.sync_batch_write(
        "test_table", delete_keys=[{"pk": pk, "sk": str(i)} for i in range(1, 4)]
    )


async def test_concurrent_exact_and_default_reads_share_a_client(account_model, dynamo):
    # GIVEN two reads with different decoding choices on the same client
    pk = f"decimal-concurrent-{uuid4()}"
    key = {"pk": pk, "sk": "1"}
    await account_model(**key, balance=EXACT).save()
    # WHEN both requests run concurrently
    exact, ordinary = await asyncio.gather(
        account_model.get(**key),
        dynamo.get_item("test_table", key),
    )
    # THEN one request cannot change the other's decoding
    assert exact.balance == EXACT
    assert type(ordinary["b"]) is float
    await dynamo.delete_item("test_table", key)


@pytest.fixture(scope="module")
def decimal_key_table(_session_client):
    name = f"decimal-keys-{uuid4().hex}"
    _session_client.sync_create_table(
        name,
        partition_key=("pk", "S"),
        sort_key=("sk", "N"),
        wait=True,
        global_secondary_indexes=[
            {
                "index_name": "group-index",
                "hash_key": ("group", "S"),
                "range_key": ("sk", "N"),
                "projection": "ALL",
            }
        ],
        local_secondary_indexes=[
            {"index_name": "amount-index", "range_key": ("amount", "N"), "projection": "ALL"}
        ],
    )
    yield name
    _session_client.sync_delete_table(name)


@pytest.mark.parametrize("mode", ["sync", "async"])
async def test_decimal_keys_pagination_and_secondary_indexes(dynamo, decimal_key_table, mode):
    # GIVEN exact numeric sort keys that collapse to the same float
    class Entry(Model):
        model_config = ModelConfig(table=decimal_key_table, client=dynamo)
        pk = StringAttribute(partition_key=True)
        sk = DecimalAttribute(sort_key=True)
        group = StringAttribute()
        amount = DecimalAttribute()
        by_group = GlobalSecondaryIndex(
            index_name="group-index", partition_key="group", sort_key="sk"
        )
        by_amount = LocalSecondaryIndex(index_name="amount-index", sort_key="amount")

    pk = str(uuid4())
    values = [
        Decimal("1.1234567890123456789012345678901234567"),
        Decimal("1.1234567890123456789012345678901234568"),
    ]
    for value in values:
        Entry(pk=pk, sk=value, group=pk, amount=value).sync_save()
    # WHEN paginating one item at a time, including index queries
    if mode == "sync":
        results = list(Entry.sync_query(pk, page_size=1))
        gsi = list(Entry.by_group.sync_query(pk, page_size=1))
        lsi = list(Entry.by_amount.sync_query(pk, page_size=1))
        page = Entry.sync_query(pk, limit=1)
        first = list(page)
        rest = list(Entry.sync_query(pk, last_evaluated_key=page.last_evaluated_key))
    else:
        results = [item async for item in Entry.query(pk, page_size=1)]
        gsi = [item async for item in Entry.by_group.query(pk, page_size=1)]
        lsi = [item async for item in Entry.by_amount.query(pk, page_size=1)]
        page = Entry.query(pk, limit=1)
        first = [item async for item in page]
        rest = [item async for item in Entry.query(pk, last_evaluated_key=page.last_evaluated_key)]
    # THEN continuation keys and all returned values remain exact
    for items in (results, gsi, lsi, first + rest):
        assert [item.sk for item in items] == values
        assert [item.amount for item in items] == values
    assert type(page.last_evaluated_key["sk"]) is Decimal


async def test_decimal_condition_compares_without_rounding(account_model):
    # GIVEN two values differing past float precision
    pk = str(uuid4())
    item = account_model(pk=pk, sk="1", balance=EXACT)
    await item.save()
    # WHEN a condition uses the wrong exact value
    with pytest.raises(ConditionalCheckFailedException):
        await item.update(
            atomic=[account_model.balance.set(Decimal("0"))],
            condition=account_model.balance == Decimal("12345678901234567890.123456789012345679"),
        )
    # THEN the failed update leaves the original number intact
    assert (await account_model.get(pk=pk, sk="1")).balance == EXACT
    await item.delete()


@pytest.mark.parametrize("mode", ["sync", "async"])
async def test_collection_hydrates_decimal_and_number_members(dynamo, mode):
    # GIVEN different numeric declarations under the same alias
    from pydynox import Collection

    class Event(Model):
        model_config = ModelConfig(table="test_table", client=dynamo)
        pk = StringAttribute(partition_key=True)
        sk = StringAttribute(sort_key=True)
        kind = StringAttribute(discriminator=True)

    class Payment(Event):
        amount = DecimalAttribute(alias="a")

    class Measurement(Event):
        amount = NumberAttribute(alias="a")

    pk = str(uuid4())
    payment = Payment(pk=pk, sk="PAYMENT", amount=EXACT)
    measurement = Measurement(pk=pk, sk="MEASUREMENT", amount=0.25)
    payment.sync_save()
    measurement.sync_save()
    # WHEN a collection loads both models in one request
    collection = Collection([Payment, Measurement])
    result = collection.sync_query(pk=pk) if mode == "sync" else await collection.query(pk=pk)
    # THEN the concrete model determines the Python numeric type
    assert result.payments[0].amount == EXACT
    assert type(result.measurements[0].amount) is float
    payment.sync_delete()
    measurement.sync_delete()


async def test_unknown_discriminator_preserves_parent_number_decoding(dynamo):
    # GIVEN a NumberAttribute parent with a decimal subclass
    class Event(Model):
        model_config = ModelConfig(table="test_table", client=dynamo)
        pk = StringAttribute(partition_key=True)
        sk = StringAttribute(sort_key=True)
        kind = StringAttribute(discriminator=True)
        amount = NumberAttribute()

    class Payment(Event):
        amount = DecimalAttribute()

    key = {"pk": str(uuid4()), "sk": "unknown"}
    await dynamo.put_item("test_table", {**key, "kind": "UnknownEvent", "amount": Decimal("1.25")})
    try:
        # WHEN loading an item whose discriminator falls back to the parent
        loaded = await Event.get(**key)
        raw = await Event.get(**key, as_dict=True)
        # THEN neither model hydration nor as_dict changes NumberAttribute's type
        assert type(loaded) is Event
        assert type(loaded.amount) is float
        assert type(raw["amount"]) is float
    finally:
        await dynamo.delete_item("test_table", key)
