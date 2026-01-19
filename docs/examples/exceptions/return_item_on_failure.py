from pydynox import DynamoDBClient
from pydynox.pydynox_core import ConditionalCheckFailedException


def optimistic_lock_with_item_return():
    """Update with version check, get existing item on failure."""
    client = DynamoDBClient()

    # Try to update with version check
    try:
        client.update_item(
            "users",
            {"pk": "USER#123"},
            updates={"name": "Alice", "version": 2},
            condition_expression="#v = :expected",
            expression_attribute_names={"#v": "version"},
            expression_attribute_values={":expected": 1},
            return_values_on_condition_check_failure=True,
        )
        print("Updated successfully")
    except ConditionalCheckFailedException as e:
        # No extra GET needed - item is on the exception
        print(f"Version conflict! Current item: {e.item}")
        print(f"Current version: {e.item['version']}")


def prevent_overwrite_with_item_return():
    """Create new item, get existing on conflict."""
    client = DynamoDBClient()

    try:
        client.put_item(
            "users",
            {"pk": "USER#123", "name": "Bob", "email": "bob@example.com"},
            condition_expression="attribute_not_exists(pk)",
            return_values_on_condition_check_failure=True,
        )
        print("Created new user")
    except ConditionalCheckFailedException as e:
        # See what's already there without extra GET
        print(f"User already exists: {e.item['name']}")
