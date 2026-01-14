from pydynox import DynamoDBClient

client = DynamoDBClient()

# get_item with projection - pass a list of field names
item = client.get_item(
    "users",
    {"pk": "USER#1"},
    projection=["name", "email"],
)
# Returns only: {"pk": "USER#1", "name": "John", "email": "john@example.com"}

# query with projection_expression
for item in client.query(
    "users",
    key_condition_expression="pk = :pk",
    projection_expression="#n, email",
    expression_attribute_names={"#n": "name"},
    expression_attribute_values={":pk": "USER#123"},
):
    print(item.get("email"))
