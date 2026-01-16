from pydynox import DynamoDBClient
from pydynox.pydynox_core import (
    ConnectionException,
    CredentialsException,
    PydynoxException,
    ResourceNotFoundException,
)


def safe_get_item():
    client = DynamoDBClient()

    try:
        item = client.get_item("users", {"pk": "USER#123"})
        return item
    except ResourceNotFoundException:
        print("Table does not exist")
    except CredentialsException:
        print("Check your AWS credentials")
    except ConnectionException:
        print("Cannot connect to DynamoDB")
    except PydynoxException as e:
        print(f"Something went wrong: {e}")
