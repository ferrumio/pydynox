from pydynox import DynamoDBClient


def create_provisioned_table():
    client = DynamoDBClient()

    # Provisioned capacity (fixed cost, predictable performance)
    client.create_table(
        "high_traffic_table",
        hash_key=("pk", "S"),
        billing_mode="PROVISIONED",
        read_capacity=100,
        write_capacity=50,
        wait=True,
    )


def create_encrypted_table():
    client = DynamoDBClient()

    # Customer managed KMS encryption
    client.create_table(
        "sensitive_data",
        hash_key=("pk", "S"),
        encryption="CUSTOMER_MANAGED",
        kms_key_id="arn:aws:kms:us-east-1:123456789:key/abc-123",
        wait=True,
    )


def create_infrequent_access_table():
    client = DynamoDBClient()

    # Infrequent access class (cheaper storage, higher read cost)
    client.create_table(
        "archive",
        hash_key=("pk", "S"),
        table_class="STANDARD_INFREQUENT_ACCESS",
        wait=True,
    )
