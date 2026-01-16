from pydynox import DynamoDBClient
from pydynox.pydynox_core import ConditionalCheckFailedException


def update_if_exists():
    client = DynamoDBClient()

    try:
        client.update_item(
            "users",
            {"pk": "USER#123"},
            updates={"name": "John"},
            condition_expression="attribute_exists(pk)",
        )
        print("Updated successfully")
    except ConditionalCheckFailedException:
        print("Item does not exist, cannot update")
