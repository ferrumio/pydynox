from pydynox import DynamoDBClient

client = DynamoDBClient()

client.create_table(
    "products",
    hash_key=("pk", "S"),
    range_key=("sk", "S"),
    global_secondary_indexes=[
        {
            "index_name": "location-index",
            "hash_keys": [("tenant_id", "S"), ("region", "S")],
            "range_keys": [("created_at", "S"), ("item_id", "S")],
            "projection": "ALL",
        },
        {
            "index_name": "category-index",
            "hash_keys": [("category", "S"), ("subcategory", "S")],
            "projection": "ALL",
        },
    ],
)
