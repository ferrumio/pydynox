"""Exact decimal values must survive serialization and model reads."""

from decimal import Decimal, localcontext

import pytest
from pydynox import Model, ModelConfig, pydynox_core
from pydynox.attributes import DecimalAttribute, NumberAttribute, StringAttribute
from pydynox.testing import MemoryBackend

EXACT = Decimal("12345678901234567890.123456789012345678")


class Account(Model):
    model_config = ModelConfig(table="decimal_accounts")
    pk = StringAttribute(partition_key=True)
    sk = StringAttribute(sort_key=True)
    balance = DecimalAttribute(alias="b")
    count = NumberAttribute()
    ratio = NumberAttribute()


@pytest.mark.parametrize(
    "text",
    [
        "0",
        "-0.000",
        "1.2300",
        "-0.000123",
        str(EXACT),
        "99999999999999999999999999999999999999",
        "1E-130",
        "-1E-130",
        "9.9999999999999999999999999999999999999E125",
        "1E125",
        "1000.00",
    ],
)
def test_exact_round_trip_ignores_arithmetic_context(text):
    # GIVEN an exact value and an intentionally small arithmetic precision
    value = Decimal(text)
    with localcontext() as context:
        context.prec = 6
        # WHEN Rust serializes and decodes the number
        encoded = pydynox_core.item_to_dynamo({"amount": value, "count": 2, "ratio": 0.5})
        result = pydynox_core.item_from_dynamo(
            encoded, _number_schema={"fields": {"amount"}, "variants": {}}
        )
        # THEN no float or Decimal arithmetic context rounds the value
        assert Decimal(encoded["amount"]["N"]) == value
        assert result["amount"] == value
        assert type(result["amount"]) is Decimal
        assert type(result["count"]) is int
        assert type(result["ratio"]) is float
        assert context.prec == 6


@pytest.mark.parametrize(
    "text",
    [
        "NaN",
        "sNaN",
        "Infinity",
        "-Infinity",
        "1E126",
        "1E-131",
        "1.23456789012345678901234567890123456789",
    ],
)
def test_invalid_decimal_rejected_before_write(text):
    # GIVEN a number outside DynamoDB's finite precision and range
    value = Decimal(text)
    # WHEN using either the attribute or the raw serializer
    for convert in (DecimalAttribute().serialize, pydynox_core.py_to_dynamo):
        # THEN validation fails instead of rounding
        with pytest.raises(ValueError):
            convert(value)


@pytest.mark.parametrize("value", [1.23, "1.23", True, False])
def test_decimal_attribute_rejects_inexact_or_wrong_input(value):
    # GIVEN an input that requires a caller's explicit conversion
    attribute = DecimalAttribute()
    # WHEN assigning, decoding, or building an atomic update
    for convert in (
        attribute.serialize,
        attribute.deserialize,
        attribute.set,
        attribute.add,
        attribute.if_not_exists,
    ):
        # THEN it is rejected before a request is sent
        with pytest.raises(TypeError, match="Decimal or int"):
            convert(value)
    with pytest.raises(TypeError):
        Account(pk="a", balance=value)


def test_integer_default_none_alias_and_change_tracking():
    # GIVEN an aliased decimal field loaded from DynamoDB
    account = Account.from_dict({"pk": "a", "b": 42, "count": 2, "ratio": 0.5})
    # THEN integers normalize to Decimal and unchanged values stay clean
    assert type(account.balance) is Decimal
    assert account.balance == Decimal(42)
    assert not account.is_dirty
    account.balance = 42
    assert not account.is_dirty
    # WHEN a precise fractional value is assigned
    account.balance = EXACT
    assert account.is_dirty
    assert account.to_dict()["b"] == EXACT
    assert Account(pk="b").balance is None


def test_model_reads_select_decimals_without_changing_number_attribute():
    # GIVEN a model with both decimal and ordinary numeric fields
    with MemoryBackend() as backend:
        Account(pk="a", sk="1", balance=EXACT, count=7, ratio=0.25).sync_save()
        # WHEN reading through models and raw dicts
        model = Account.sync_get(pk="a", sk="1")
        raw = backend.client.sync_get_item("decimal_accounts", {"pk": "a", "sk": "1"})
        exact_dict = Account.sync_get(pk="a", sk="1", as_dict=True)
        # THEN the model chooses exact fields while raw defaults stay compatible
        assert model.balance == EXACT
        assert type(model.balance) is Decimal
        assert type(model.count) is int
        assert type(model.ratio) is float
        assert type(raw["b"]) is float
        assert exact_dict["b"] == EXACT
        assert Account.sync_batch_get([{"pk": "a", "sk": "1"}])[0].balance == EXACT
        assert list(Account.sync_query("a"))[0].balance == EXACT
        assert list(Account.sync_scan())[0].balance == EXACT


async def test_memory_async_reads_and_exact_atomic_arithmetic():
    # GIVEN 38 significant digits and a small application context
    with MemoryBackend(), localcontext() as context:
        context.prec = 6
        account = Account(pk="a", sk="1", balance=EXACT)
        await account.save()
        # WHEN DynamoDB-style arithmetic increments the last decimal place
        await account.update(atomic=[Account.balance.add(Decimal("0.000000000000000001"))])
        expected = Decimal("12345678901234567890.123456789012345679")
        # THEN all supported async read paths retain the result
        assert (await Account.get(pk="a", sk="1")).balance == expected
        assert (await Account.batch_get([{"pk": "a", "sk": "1"}]))[0].balance == expected
        assert [item.balance async for item in Account.query("a")] == [expected]
        assert [item.balance async for item in Account.scan()] == [expected]
        assert context.prec == 6


def test_polymorphic_read_preserves_each_models_numeric_type():
    # GIVEN two subclasses sharing a stored attribute name
    class Event(Model):
        model_config = ModelConfig(table="decimal_events")
        pk = StringAttribute(partition_key=True)
        sk = StringAttribute(sort_key=True)
        kind = StringAttribute(discriminator=True)

    class Payment(Event):
        amount = DecimalAttribute(alias="a")

    class Measurement(Event):
        amount = NumberAttribute(alias="a")

    with MemoryBackend():
        Payment(pk="p", sk="1", amount=EXACT).sync_save()
        Measurement(pk="p", sk="2", amount=0.25).sync_save()
        # WHEN the parent loads both subclasses in one query
        results = list(Event.sync_query("p"))
        # THEN only the DecimalAttribute model exposes Decimal
        assert isinstance(results[0], Payment)
        assert results[0].amount == EXACT
        assert type(results[1].amount) is float


def test_raw_nested_decimal_writes_and_top_level_selection():
    # GIVEN decimal values in raw nested data
    item = {"amount": EXACT, "metadata": {"amount": Decimal("1.25")}, "samples": [Decimal("0.5")]}
    # WHEN using the raw item helpers
    encoded = pydynox_core.item_to_dynamo(item)
    result = pydynox_core.item_from_dynamo(
        encoded, _number_schema={"fields": {"amount", "metadata", "missing"}, "variants": {}}
    )
    # THEN selection applies to top-level scalar N values only
    assert result["amount"] == EXACT
    assert result["metadata"] == {"amount": 1.25}
    assert result["samples"] == [0.5]


def test_lazy_model_query_keeps_its_schema_private():
    # GIVEN a model query and an ordinary raw query sharing one backend
    from pydynox.query import QueryResult

    with MemoryBackend() as backend:
        Account(pk="a", sk="1", balance=EXACT).sync_save()
        exact = Account.sync_query("a")
        ordinary = QueryResult(
            backend.client,
            "decimal_accounts",
            "pk = :pk",
            expression_attribute_values={":pk": "a"},
        )
        # WHEN the raw query runs before the model query
        raw = list(ordinary)
        typed = list(exact)
        # THEN neither query changes the other's decoding
        assert type(raw[0]["b"]) is float
        assert typed[0].balance == EXACT


def test_decimal_default_and_size_use_numeric_representation():
    # GIVEN an integer default and a decimal with insignificant zeros
    from pydynox.size import calculate_attribute_size

    class Balance(Model):
        pk = StringAttribute(partition_key=True)
        amount = DecimalAttribute(default=42)

    # THEN defaults have the declared type and size counts significant digits
    assert type(Balance(pk="a").amount) is Decimal
    assert calculate_attribute_size(Decimal("1.230000E125")) == 3
    assert calculate_attribute_size(Decimal("0E-100")) == 1


async def test_vector_model_projection_keeps_decimal_values():
    # GIVEN a projected decimal field in an in-memory vector index
    from pydynox.attributes import VectorAttribute
    from pydynox.indexes import VectorIndex

    class Product(Model):
        model_config = ModelConfig(table="decimal_products")
        pk = StringAttribute(partition_key=True)
        price = DecimalAttribute(alias="p")
        embedding = VectorAttribute(dimensions=2)
        semantic = VectorIndex(
            index_name="semantic", vector_attribute="embedding", projection=["price"]
        )

    with MemoryBackend():
        await Product.create_table()
        await Product(pk="a", price=EXACT, embedding=[1.0, 0.0]).save()
        # WHEN searching through both APIs, with and without model hydration
        sync = Product.semantic.sync_search([1.0, 0.0])
        asynchronous = await Product.semantic.search([1.0, 0.0])
        raw = await Product.semantic.search([1.0, 0.0], as_dict=True)
        # THEN the projected alias is decoded exactly
        assert sync[0].item.price == EXACT
        assert asynchronous[0].item.price == EXACT
        assert raw[0].item["p"] == EXACT


def test_memory_rejects_invalid_decimal_in_update_expression():
    # GIVEN a valid stored balance
    with MemoryBackend() as backend:
        Account(pk="a", sk="1", balance=EXACT).sync_save()
        # WHEN a raw update contains an invalid Decimal
        with pytest.raises(ValueError):
            backend.client.sync_update_item(
                "decimal_accounts",
                {"pk": "a", "sk": "1"},
                update_expression="SET b = :b",
                expression_attribute_values={":b": Decimal("NaN")},
            )
        # THEN validation happens before the stored value changes
        assert Account.sync_get(pk="a", sk="1").balance == EXACT


@pytest.mark.parametrize(
    "written,read", [("1.00", "1"), ("1E2", "100.0"), ("0.00", "-0"), ("1E-130", "0.1E-129")]
)
def test_memory_decimal_keys_compare_values(written, read):
    # GIVEN a numeric key written with a different decimal representation
    class Entry(Model):
        model_config = ModelConfig(table="decimal_keys")
        pk = StringAttribute(partition_key=True)
        sk = DecimalAttribute(sort_key=True)
        amount = DecimalAttribute()

    with MemoryBackend():
        Entry(pk="a", sk=Decimal(written), amount=EXACT).sync_save()
        # WHEN looking up the same numeric value using different notation
        loaded = Entry.sync_get(pk="a", sk=Decimal(read))
        # THEN the item is found without losing precision in either field
        assert loaded.sk == Decimal(read)
        assert loaded.amount == EXACT


@pytest.mark.parametrize("method", ["put_item", "sync_put_item"])
@pytest.mark.parametrize(
    "text",
    [
        "NaN",
        "sNaN",
        "Infinity",
        "-Infinity",
        "1E126",
        "1E-131",
        "1.23456789012345678901234567890123456789",
    ],
)
def test_native_requests_reject_invalid_decimals_before_io(method, text):
    # GIVEN the direct SDK conversion path and an unreachable endpoint
    client = pydynox_core.DynamoDBClient(
        region="us-east-1",
        access_key="testing",
        secret_key="testing",
        endpoint_url="http://127.0.0.1:1",
    )
    # WHEN preparing either a sync request or an async awaitable
    # THEN validation fails locally without attempting a network request
    with pytest.raises(ValueError):
        getattr(client, method)("accounts", {"pk": "a", "amount": Decimal(text)})


@pytest.mark.parametrize("value", [EXACT, Decimal("1E-130"), Decimal("42"), 42, 0.25])
def test_number_attribute_preserves_caller_supplied_values(value):
    # GIVEN a NumberAttribute receiving an application-owned value
    class Measurement(Model):
        pk = StringAttribute(partition_key=True)
        amount = NumberAttribute(alias="a")

    data = {"pk": "a", "a": value}
    # WHEN loading a dictionary, as supported before DecimalAttribute existed
    loaded = Measurement.from_dict(data)
    # THEN deserialization preserves both the object and its numeric precision
    assert loaded.amount is value
    assert loaded.to_dict()["a"] is value
    assert data["a"] is value
    assert not loaded.is_dirty


def test_public_read_apis_do_not_expose_decimal_configuration():
    # GIVEN the public client, iterator, and MemoryBackend APIs
    import inspect

    from pydynox import DynamoDBClient
    from pydynox.query import AsyncQueryResult, AsyncScanResult, QueryResult, ScanResult
    from pydynox.testing.memory import MemoryClient

    readers = [QueryResult, AsyncQueryResult, ScanResult, AsyncScanResult]
    for client in (DynamoDBClient, MemoryClient):
        for name in ("get_item", "query", "scan", "batch_get", "search_vectors"):
            readers.append(getattr(client, name))
            if hasattr(client, f"sync_{name}"):
                readers.append(getattr(client, f"sync_{name}"))
    # THEN numeric decoding is not a caller-facing option
    for reader in readers:
        parameters = inspect.signature(reader).parameters
        assert "decimal_fields" not in parameters
        assert "_number_schema" not in parameters


async def test_memory_model_reads_share_metrics_without_changing_raw_decoding():
    # GIVEN a model and a raw read using the same backend
    import asyncio

    with MemoryBackend() as backend:
        await Account(pk="a", sk="1", balance=EXACT).save()
        # WHEN both read APIs run in the same task group
        exact, raw = await asyncio.gather(
            Account.get(pk="a", sk="1"),
            backend.client.get_item("decimal_accounts", {"pk": "a", "sk": "1"}),
        )
        # THEN decoding stays separate and metrics reach the original client
        assert exact.balance == EXACT
        assert type(raw["b"]) is float
        assert backend.client.get_total_metrics().get_count == 2
        assert backend.client.get_last_metrics() is not None


@pytest.mark.parametrize("number", ["1", "1.0", "1E3"])
def test_polymorphic_native_decoding_uses_each_models_number_type(number):
    # GIVEN two model variants sharing the same DynamoDB field
    schema = {
        "fields": {"amount"},
        "variants": {"kind": {"Payment": {"amount"}, "Measurement": set()}},
    }
    # WHEN the number arrives through the native decoder
    payment = pydynox_core.item_from_dynamo(
        {"kind": {"S": "Payment"}, "amount": {"N": number}},
        _number_schema=schema,
    )
    measurement = pydynox_core.item_from_dynamo(
        {"kind": {"S": "Measurement"}, "amount": {"N": number}},
        _number_schema=schema,
    )
    ordinary = pydynox_core.dynamo_to_py({"N": number})
    # THEN the exact model gets Decimal and NumberAttribute keeps the wire type
    assert payment["amount"] == Decimal(number)
    assert type(payment["amount"]) is Decimal
    assert measurement["amount"] == ordinary
    assert type(measurement["amount"]) is type(ordinary)


@pytest.mark.parametrize(
    "attribute,expected_type", [(NumberAttribute, float), (DecimalAttribute, Decimal)]
)
def test_unknown_discriminator_uses_the_parent_numeric_type(attribute, expected_type):
    # GIVEN an item whose model subclass is not registered in this application
    class Event(Model):
        model_config = ModelConfig(table="decimal_events")
        pk = StringAttribute(partition_key=True)
        kind = StringAttribute(discriminator=True)
        amount = attribute()

    class Payment(Event):
        amount = DecimalAttribute()

    with MemoryBackend() as backend:
        backend.client.sync_put_item(
            "decimal_events", {"pk": "a", "kind": "UnknownEvent", "amount": Decimal("1.25")}
        )
        # WHEN normal model resolution falls back to the parent class
        loaded = Event.sync_get(pk="a")
        # THEN the parent's declared numeric type still controls decoding
        assert type(loaded) is Event
        assert type(loaded.amount) is expected_type


@pytest.mark.parametrize("exact", [False, True])
def test_native_unknown_discriminator_uses_fallback_schema(exact):
    # GIVEN a parent schema and an unknown discriminator value
    schema = {
        "fields": {"amount"},
        "variants": {"kind": {"Payment": {"amount"}}},
        "fallback_fields": {"amount"} if exact else set(),
    }
    # WHEN decoding the original DynamoDB number text
    item = pydynox_core.item_from_dynamo(
        {"kind": {"S": "UnknownEvent"}, "amount": {"N": "1.25"}},
        _number_schema=schema,
    )
    # THEN the parent schema determines the type
    assert type(item["amount"]) is (Decimal if exact else float)
