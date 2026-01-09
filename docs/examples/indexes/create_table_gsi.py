from pydynox import DynamoDBClient

client = DynamoDBClient()

# Create table with GSI (skip if already exists)
if not client.table_exists("users_with_gsi"):
    client.create_table(
        "users_with_gsi",
        hash_key=("pk", "S"),
        range_key=("sk", "S"),
        global_secondary_indexes=[
            {
                "index_name": "email-index",
                "hash_key": ("email", "S"),
                "projection": "ALL",
            },
            {
                "index_name": "status-index",
                "hash_key": ("status", "S"),
                "range_key": ("pk", "S"),
                "projection": "ALL",
            },
        ],
    )
