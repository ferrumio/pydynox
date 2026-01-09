import logging

from pydynox import DynamoDBClient

# Enable INFO level logs for pydynox
logging.basicConfig(level=logging.INFO)

client = DynamoDBClient()

# All operations are logged automatically
client.put_item("users", {"pk": "USER#1", "sk": "PROFILE", "name": "John"})
# INFO:pydynox:put_item table=users duration_ms=8.2 wcu=1.0

client.get_item("users", {"pk": "USER#1", "sk": "PROFILE"})
# INFO:pydynox:get_item table=users duration_ms=12.1 rcu=0.5
