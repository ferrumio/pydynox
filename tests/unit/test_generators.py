"""Tests for auto-generate strategies."""

import re
import time

import pytest
from pydynox.generators import AutoGenerate, generate_value, is_auto_generate


def test_is_auto_generate_true():
    """is_auto_generate should return True for AutoGenerate enums."""
    assert is_auto_generate(AutoGenerate.UUID4)
    assert is_auto_generate(AutoGenerate.ULID)
    assert is_auto_generate(AutoGenerate.KSUID)
    assert is_auto_generate(AutoGenerate.EPOCH)
    assert is_auto_generate(AutoGenerate.EPOCH_MS)
    assert is_auto_generate(AutoGenerate.ISO8601)


def test_is_auto_generate_false():
    """is_auto_generate should return False for non-AutoGenerate values."""
    assert not is_auto_generate("uuid4")
    assert not is_auto_generate(None)
    assert not is_auto_generate(123)
    assert not is_auto_generate({"key": "value"})


def test_uuid4_format():
    """UUID4 should be 36 chars with valid format."""
    value = generate_value(AutoGenerate.UUID4)
    assert len(value) == 36
    assert value.count("-") == 4
    pattern = r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
    assert re.match(pattern, value), f"Invalid UUID4: {value}"


def test_uuid4_unique():
    """Each UUID4 should be unique."""
    values = [generate_value(AutoGenerate.UUID4) for _ in range(100)]
    assert len(set(values)) == 100


def test_ulid_format():
    """ULID should be 26 chars, Crockford base32."""
    value = generate_value(AutoGenerate.ULID)
    assert len(value) == 26
    assert all(c in "0123456789ABCDEFGHJKMNPQRSTVWXYZ" for c in value)


def test_ulid_sortable():
    """ULIDs generated later should sort after earlier ones."""
    ulid1 = generate_value(AutoGenerate.ULID)
    time.sleep(0.002)
    ulid2 = generate_value(AutoGenerate.ULID)
    assert ulid2 > ulid1


def test_ksuid_format():
    """KSUID should be 27 chars, base62."""
    value = generate_value(AutoGenerate.KSUID)
    assert len(value) == 27
    assert all(c.isalnum() for c in value)


def test_ksuid_unique():
    """Each KSUID should be unique."""
    values = [generate_value(AutoGenerate.KSUID) for _ in range(100)]
    assert len(set(values)) == 100


def test_epoch_returns_int():
    """EPOCH should return current time in seconds."""
    before = int(time.time())
    value = generate_value(AutoGenerate.EPOCH)
    after = int(time.time())
    assert isinstance(value, int)
    assert before <= value <= after


def test_epoch_ms_returns_int():
    """EPOCH_MS should return current time in milliseconds."""
    before = int(time.time() * 1000)
    value = generate_value(AutoGenerate.EPOCH_MS)
    after = int(time.time() * 1000)
    assert isinstance(value, int)
    assert before <= value <= after + 10


def test_iso8601_format():
    """ISO8601 should be proper format."""
    value = generate_value(AutoGenerate.ISO8601)
    assert len(value) == 20
    assert value.endswith("Z")
    pattern = r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$"
    assert re.match(pattern, value), f"Invalid ISO8601: {value}"


@pytest.mark.parametrize(
    "strategy,expected_type,expected_len",
    [
        pytest.param(AutoGenerate.UUID4, str, 36, id="uuid4"),
        pytest.param(AutoGenerate.ULID, str, 26, id="ulid"),
        pytest.param(AutoGenerate.KSUID, str, 27, id="ksuid"),
        pytest.param(AutoGenerate.ISO8601, str, 20, id="iso8601"),
    ],
)
def test_string_strategies(strategy, expected_type, expected_len):
    """String strategies should return correct type and length."""
    value = generate_value(strategy)
    assert isinstance(value, expected_type)
    assert len(value) == expected_len


@pytest.mark.parametrize(
    "strategy",
    [
        pytest.param(AutoGenerate.EPOCH, id="epoch"),
        pytest.param(AutoGenerate.EPOCH_MS, id="epoch_ms"),
    ],
)
def test_number_strategies(strategy):
    """Number strategies should return positive integers."""
    value = generate_value(strategy)
    assert isinstance(value, int)
    assert value > 0
