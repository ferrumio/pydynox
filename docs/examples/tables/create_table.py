from pydynox import DynamoDBClient


def create_users_table():
    client = DynamoDBClient()

    # Simple table with hash key only
    client.create_table(
        "users",
        hash_key=("pk", "S"),
        wait=True,  # Wait for table to be ready
    )


def create_orders_table():
    client = DynamoDBClient()

    # Table with hash key and range key
    client.create_table(
        "orders",
        hash_key=("pk", "S"),
        range_key=("sk", "S"),
        wait=True,
    )
