"""Sync integration tests for return_values on put, delete, and update."""

import pytest

# ========== PUT_ITEM ==========


def test_sync_put_item_return_values_all_old_existing(dynamo):
    """Test put_item with return_values=ALL_OLD returns the old item."""
    # GIVEN an existing item
    item = {"pk": "SYNC_RV_PUT#1", "sk": "PROFILE", "name": "Original", "age": 25}
    dynamo.sync_put_item("test_table", item)

    # WHEN overwriting with return_values=ALL_OLD
    new_item = {"pk": "SYNC_RV_PUT#1", "sk": "PROFILE", "name": "Updated", "age": 30}
    old_item = dynamo.sync_put_item("test_table", new_item, return_values="ALL_OLD")

    # THEN old item is returned
    assert old_item is not None
    assert old_item["name"] == "Original"
    assert old_item["age"] == 25

    # AND metrics are available via get_last_metrics()
    assert dynamo.get_last_metrics().duration_ms > 0


def test_sync_put_item_return_values_all_old_new_item(dynamo):
    """Test put_item with return_values=ALL_OLD on new item returns None."""
    item = {"pk": "SYNC_RV_PUT#2", "sk": "PROFILE", "name": "New"}
    old_item = dynamo.sync_put_item("test_table", item, return_values="ALL_OLD")

    assert old_item is None
    assert dynamo.get_last_metrics().duration_ms > 0


def test_sync_put_item_return_values_none_returns_metrics(dynamo):
    """Test put_item with return_values=NONE returns just metrics."""
    item = {"pk": "SYNC_RV_PUT#3", "sk": "PROFILE", "name": "Test"}
    metrics = dynamo.sync_put_item("test_table", item, return_values="NONE")

    assert metrics.duration_ms > 0


def test_sync_put_item_no_return_values_backward_compat(dynamo):
    """Test put_item without return_values still returns just metrics."""
    item = {"pk": "SYNC_RV_PUT#4", "sk": "PROFILE", "name": "Test"}
    metrics = dynamo.sync_put_item("test_table", item)

    assert metrics.duration_ms > 0


def test_sync_put_item_return_values_invalid_raises(dynamo):
    """Test put_item with invalid return_values raises ValueError."""
    item = {"pk": "SYNC_RV_PUT#5", "sk": "PROFILE", "name": "Test"}

    with pytest.raises(ValueError, match="Invalid return_values for put_item"):
        dynamo.sync_put_item("test_table", item, return_values="ALL_NEW")


# ========== DELETE_ITEM ==========


def test_sync_delete_item_return_values_all_old(dynamo):
    """Test delete_item with return_values=ALL_OLD returns the deleted item."""
    # GIVEN an existing item
    item = {"pk": "SYNC_RV_DEL#1", "sk": "PROFILE", "name": "ToDelete", "score": 42}
    dynamo.sync_put_item("test_table", item)

    # WHEN deleting with return_values=ALL_OLD
    deleted_item = dynamo.sync_delete_item(
        "test_table",
        {"pk": "SYNC_RV_DEL#1", "sk": "PROFILE"},
        return_values="ALL_OLD",
    )

    # THEN deleted item is returned
    assert deleted_item is not None
    assert deleted_item["name"] == "ToDelete"
    assert deleted_item["score"] == 42
    assert dynamo.get_last_metrics().duration_ms > 0

    # AND item is actually gone
    result = dynamo.sync_get_item("test_table", {"pk": "SYNC_RV_DEL#1", "sk": "PROFILE"})
    assert result is None


def test_sync_delete_item_return_values_all_old_nonexistent(dynamo):
    """Test delete_item with return_values=ALL_OLD on missing item returns None."""
    deleted_item = dynamo.sync_delete_item(
        "test_table",
        {"pk": "SYNC_RV_DEL#GHOST", "sk": "NONE"},
        return_values="ALL_OLD",
    )

    assert deleted_item is None
    assert dynamo.get_last_metrics().duration_ms > 0


def test_sync_delete_item_no_return_values_backward_compat(dynamo):
    """Test delete_item without return_values still returns just metrics."""
    item = {"pk": "SYNC_RV_DEL#2", "sk": "PROFILE", "name": "Test"}
    dynamo.sync_put_item("test_table", item)

    metrics = dynamo.sync_delete_item("test_table", {"pk": "SYNC_RV_DEL#2", "sk": "PROFILE"})
    assert metrics.duration_ms > 0


def test_sync_delete_item_return_values_invalid_raises(dynamo):
    """Test delete_item with invalid return_values raises ValueError."""
    with pytest.raises(ValueError, match="Invalid return_values for delete_item"):
        dynamo.sync_delete_item(
            "test_table",
            {"pk": "SYNC_RV_DEL#X", "sk": "Y"},
            return_values="ALL_NEW",
        )


# ========== UPDATE_ITEM ==========


@pytest.mark.parametrize(
    "return_values, expected_keys",
    [
        pytest.param("ALL_NEW", {"pk", "sk", "name", "age"}, id="ALL_NEW"),
        pytest.param("UPDATED_NEW", {"name", "age"}, id="UPDATED_NEW"),
        pytest.param("ALL_OLD", {"pk", "sk", "name", "age"}, id="ALL_OLD"),
        pytest.param("UPDATED_OLD", {"name", "age"}, id="UPDATED_OLD"),
    ],
)
def test_sync_update_item_return_values_modes(dynamo, return_values, expected_keys):
    """Test update_item with different return_values modes."""
    pk = f"SYNC_RV_UPD#{return_values}"

    # GIVEN an existing item
    item = {"pk": pk, "sk": "PROFILE", "name": "Original", "age": 25}
    dynamo.sync_put_item("test_table", item)

    # WHEN updating with return_values
    attrs = dynamo.sync_update_item(
        "test_table",
        {"pk": pk, "sk": "PROFILE"},
        updates={"name": "Updated", "age": 30},
        return_values=return_values,
    )

    # THEN attributes are returned
    assert attrs is not None
    assert expected_keys.issubset(set(attrs.keys()))
    assert dynamo.get_last_metrics().duration_ms > 0

    # Check values based on mode
    if return_values in ("ALL_NEW", "UPDATED_NEW"):
        assert attrs["name"] == "Updated"
        assert attrs["age"] == 30
    elif return_values in ("ALL_OLD", "UPDATED_OLD"):
        assert attrs["name"] == "Original"
        assert attrs["age"] == 25


def test_sync_update_item_return_values_all_new_full_item(dynamo):
    """Test ALL_NEW returns the complete item after update."""
    item = {"pk": "SYNC_RV_UPD#FULL", "sk": "PROFILE", "name": "Test", "status": "active"}
    dynamo.sync_put_item("test_table", item)

    attrs = dynamo.sync_update_item(
        "test_table",
        {"pk": "SYNC_RV_UPD#FULL", "sk": "PROFILE"},
        updates={"name": "Changed"},
        return_values="ALL_NEW",
    )

    # ALL_NEW returns the full item after update
    assert attrs["pk"] == "SYNC_RV_UPD#FULL"
    assert attrs["name"] == "Changed"
    assert attrs["status"] == "active"  # untouched field still there


def test_sync_update_item_no_return_values_backward_compat(dynamo):
    """Test update_item without return_values still returns just metrics."""
    item = {"pk": "SYNC_RV_UPD#COMPAT", "sk": "PROFILE", "name": "Test"}
    dynamo.sync_put_item("test_table", item)

    metrics = dynamo.sync_update_item(
        "test_table",
        {"pk": "SYNC_RV_UPD#COMPAT", "sk": "PROFILE"},
        updates={"name": "Updated"},
    )
    assert metrics.duration_ms > 0


def test_sync_update_item_return_values_invalid_raises(dynamo):
    """Test update_item with invalid return_values raises ValueError."""
    with pytest.raises(ValueError, match="Invalid return_values"):
        dynamo.sync_update_item(
            "test_table",
            {"pk": "X", "sk": "Y"},
            updates={"name": "Test"},
            return_values="INVALID",
        )
