"""Tests for large number deserialization (issue #279).

DynamoDB supports numbers with up to 38 digits. The deserialization
must handle numbers bigger than i64::MAX by using Python's arbitrary
precision integers.
"""

import pytest
from pydynox import pydynox_core

I64_MAX = 9_223_372_036_854_775_807
I64_MIN = -9_223_372_036_854_775_808


@pytest.mark.parametrize(
    "number_str,expected",
    [
        pytest.param("0", 0, id="zero"),
        pytest.param("42", 42, id="small_int"),
        pytest.param("-1", -1, id="negative"),
        pytest.param(str(I64_MAX), I64_MAX, id="i64_max"),
        pytest.param(str(I64_MIN), I64_MIN, id="i64_min"),
        pytest.param("99999999999999999999", 99999999999999999999, id="20_digits"),
        pytest.param(
            "12345678901234567890123456789",
            12345678901234567890123456789,
            id="29_digits",
        ),
        pytest.param(
            "99999999999999999999999999999999999999",
            99999999999999999999999999999999999999,
            id="38_digits_max_dynamo",
        ),
        pytest.param(
            str(I64_MAX + 1),
            I64_MAX + 1,
            id="just_above_i64_max",
        ),
        pytest.param(
            str(I64_MIN - 1),
            I64_MIN - 1,
            id="just_below_i64_min",
        ),
        pytest.param("3.14", 3.14, id="float"),
        pytest.param("1.5e10", 1.5e10, id="scientific_notation"),
    ],
)
def test_dynamo_to_py_large_numbers(number_str, expected):
    """dynamo_to_py handles numbers of any size (dict-based path)."""
    dynamo_attr = {"N": number_str}
    result = pydynox_core.dynamo_to_py(dynamo_attr)
    assert result == expected
    assert type(result) is type(expected)


@pytest.mark.parametrize(
    "number_str,expected",
    [
        pytest.param("0", 0, id="zero"),
        pytest.param("42", 42, id="small_int"),
        pytest.param(str(I64_MAX), I64_MAX, id="i64_max"),
        pytest.param("99999999999999999999", 99999999999999999999, id="20_digits"),
        pytest.param(
            "12345678901234567890123456789",
            12345678901234567890123456789,
            id="29_digits",
        ),
        pytest.param(
            "99999999999999999999999999999999999999",
            99999999999999999999999999999999999999,
            id="38_digits_max_dynamo",
        ),
        pytest.param(
            str(I64_MAX + 1),
            I64_MAX + 1,
            id="just_above_i64_max",
        ),
    ],
)
def test_item_from_dynamo_large_numbers(number_str, expected):
    """item_from_dynamo handles large numbers in items (dict-based path)."""
    dynamo_item = {"pk": {"S": "test"}, "large_num": {"N": number_str}}
    result = pydynox_core.item_from_dynamo(dynamo_item)
    assert result["large_num"] == expected


def test_dynamo_to_py_number_set_with_large_numbers():
    """dynamo_to_py handles NS sets with numbers bigger than i64."""
    dynamo_attr = {"NS": ["1", "99999999999999999999", "42"]}
    result = pydynox_core.dynamo_to_py(dynamo_attr)
    assert result == {1, 99999999999999999999, 42}


def test_dynamo_to_py_invalid_number():
    """dynamo_to_py raises ValueError for truly invalid numbers."""
    with pytest.raises(ValueError, match="Invalid number"):
        pydynox_core.dynamo_to_py({"N": "not_a_number"})


def test_roundtrip_large_number():
    """Large numbers survive a py_to_dynamo -> dynamo_to_py roundtrip."""
    big = 12345678901234567890123456789
    dynamo = pydynox_core.py_to_dynamo(big)
    result = pydynox_core.dynamo_to_py(dynamo)
    assert result == big
