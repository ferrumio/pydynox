from pydynox import DynamoDBClient

client = DynamoDBClient()


async def iterate_results():
    # Iterate with async for
    async for item in client.async_query(
        "users",
        key_condition_expression="#pk = :pk",
        expression_attribute_names={"#pk": "pk"},
        expression_attribute_values={":pk": "USER#123"},
    ):
        print(item["name"])


async def collect_results():
    # Collect all results
    items = await client.async_query(
        "users",
        key_condition_expression="#pk = :pk",
        expression_attribute_names={"#pk": "pk"},
        expression_attribute_values={":pk": "USER#123"},
    ).to_list()
    return items
