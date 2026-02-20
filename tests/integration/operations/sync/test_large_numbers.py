"""Integration tests for large number serialization/deserialization (issue #279).

DynamoDB supports numbers up to 38 digits. These tests verify that
pydynox can save AND read back numbers bigger than i64::MAX, testing
the full roundtrip through both serialization and deserialization.
"""

import pytest

I64_MAX = 9_223_372_036_854_775_807


@pytest.mark.parametrize(
    "number",
    [
        pytest.param(42, id="small_int"),
        pytest.param(I64_MAX, id="i64_max"),
        pytest.param(99999999999999999999, id="20_digits"),
        pytest.param(12345678901234567890123456789, id="29_digits"),
        pytest.param(99999999999999999999999999999999999999, id="38_digits_max_dynamo"),
        pytest.param(I64_MAX + 1, id="just_above_i64_max"),
        pytest.param(-99999999999999999999, id="large_negative"),
    ],
)
def test_sync_roundtrip_large_numbers(dynamo, number):
    """Large numbers survive a pydynox put -> get roundtrip."""
    pk = f"LARGENUM#RT#{number}"
    dynamo.sync_put_item("test_table", {"pk": pk, "sk": "TEST", "large_number": number})

    result = dynamo.sync_get_item("test_table", {"pk": pk, "sk": "TEST"})
    assert result is not None
    assert result["large_number"] == number


def test_sync_roundtrip_large_number_set(dynamo):
    """Number sets with large numbers survive a pydynox put -> get roundtrip."""
    nums = {1, 99999999999999999999, 42}
    dynamo.sync_put_item("test_table", {"pk": "LARGENUM#NS_RT", "sk": "TEST", "nums": nums})

    result = dynamo.sync_get_item("test_table", {"pk": "LARGENUM#NS_RT", "sk": "TEST"})
    assert result is not None
    assert result["nums"] == nums
