"""PartiQL SELECT specific columns."""

from pydynox import DynamoDBClient

client = DynamoDBClient()

# Select only name and age columns
result = client.execute_statement(
    "SELECT name, age FROM users WHERE pk = ? AND sk = ?",
    parameters=["USER#123", "PROFILE"],
)

for item in result:
    print(f"{item['name']} is {item['age']} years old")
