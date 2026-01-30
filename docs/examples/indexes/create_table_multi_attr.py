from pydynox import DynamoDBClient

client = DynamoDBClient()

# Create table with multi-attribute GSI (skip if already exists)
if not client.table_exists("products_multi_attr"):
    client.create_table(
        "products_multi_attr",
        partition_key=("pk", "S"),
        sort_key=("sk", "S"),
        global_secondary_indexes=[
            {
                "index_name": "location-index",
                "partition_keys": [("tenant_id", "S"), ("region", "S")],
                "sort_keys": [("created_at", "S"), ("item_id", "S")],
                "projection": "ALL",
            },
            {
                "index_name": "category-index",
                "partition_keys": [("category", "S"), ("subcategory", "S")],
                "projection": "ALL",
            },
        ],
    )
