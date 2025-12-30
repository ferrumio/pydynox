from pydynox import DynamoDBClient
from pydynox.pydynox_core import (
    ConnectionError,
    CredentialsError,
    PydynoxError,
    TableNotFoundError,
)


def safe_get_item():
    client = DynamoDBClient()

    try:
        item = client.get_item("users", {"pk": "USER#123"})
        return item
    except TableNotFoundError:
        print("Table does not exist")
    except CredentialsError:
        print("Check your AWS credentials")
    except ConnectionError:
        print("Cannot connect to DynamoDB")
    except PydynoxError as e:
        print(f"Something went wrong: {e}")
