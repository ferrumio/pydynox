"""Tests for boolean rejection in sets (issue #278).

DynamoDB only supports SS, NS, and BS sets. There is no boolean set.
Booleans must be rejected early with a clear error message.
"""

import pytest
from pydynox import pydynox_core


@pytest.mark.parametrize(
    "value",
    [
        pytest.param({True, False}, id="bool_set"),
        pytest.param({True}, id="single_true"),
        pytest.param({False}, id="single_false"),
        pytest.param(frozenset({True, False}), id="frozen_bool_set"),
    ],
)
def test_py_to_dynamo_rejects_bool_set(value):
    """py_to_dynamo raises TypeError for sets containing booleans."""
    with pytest.raises(TypeError, match="DynamoDB sets do not support booleans"):
        pydynox_core.py_to_dynamo(value)


@pytest.mark.parametrize(
    "value",
    [
        pytest.param({True, False}, id="bool_set"),
        pytest.param({True}, id="single_true"),
        pytest.param({False}, id="single_false"),
    ],
)
def test_item_to_dynamo_rejects_bool_set(value):
    """item_to_dynamo raises TypeError when an attribute is a bool set."""
    item = {"pk": "test", "flags": value}
    with pytest.raises(TypeError, match="DynamoDB sets do not support booleans"):
        pydynox_core.item_to_dynamo(item)


@pytest.mark.parametrize(
    "value",
    [
        pytest.param({1, 2, 3}, id="int_set"),
        pytest.param({1.5, 2.5}, id="float_set"),
        pytest.param({"a", "b", "c"}, id="string_set"),
        pytest.param({b"a", b"b"}, id="bytes_set"),
    ],
)
def test_valid_sets_still_work(value):
    """Normal sets (int, float, str, bytes) are not affected by the bool guard."""
    result = pydynox_core.py_to_dynamo(value)
    assert result is not None
