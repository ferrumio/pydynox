"""Integration tests for boolean rejection in sets (issue #278).

Ensures booleans in sets are caught by pydynox before reaching DynamoDB.
"""

import pytest


def test_put_item_rejects_bool_set(dynamo):
    """sync_put_item raises TypeError for a boolean set attribute."""
    item = {"pk": "BOOL_SET#1", "sk": "TEST", "flags": {True, False}}

    with pytest.raises(TypeError, match="DynamoDB sets do not support booleans"):
        dynamo.sync_put_item("test_table", item)


def test_put_item_rejects_single_bool_in_set(dynamo):
    """sync_put_item raises TypeError even for a single-element bool set."""
    item = {"pk": "BOOL_SET#2", "sk": "TEST", "flag": {True}}

    with pytest.raises(TypeError, match="DynamoDB sets do not support booleans"):
        dynamo.sync_put_item("test_table", item)


def test_put_item_bool_in_list_still_works(dynamo):
    """Booleans in lists are fine — only sets are rejected."""
    item = {"pk": "BOOL_LIST#1", "sk": "TEST", "flags": [True, False]}

    dynamo.sync_put_item("test_table", item)

    result = dynamo.sync_get_item("test_table", {"pk": "BOOL_LIST#1", "sk": "TEST"})
    assert result is not None
    assert result["flags"] == [True, False]


@pytest.mark.parametrize(
    "set_value",
    [
        pytest.param({1, 2, 3}, id="int_set"),
        pytest.param({"a", "b", "c"}, id="string_set"),
    ],
)
def test_put_item_valid_sets_roundtrip(dynamo, set_value):
    """Valid sets (int, string) still save and load correctly."""
    pk = f"VALID_SET#{id(set_value)}"
    item = {"pk": pk, "sk": "TEST", "data": set_value}

    dynamo.sync_put_item("test_table", item)

    result = dynamo.sync_get_item("test_table", {"pk": pk, "sk": "TEST"})
    assert result is not None
    assert result["data"] == set_value
