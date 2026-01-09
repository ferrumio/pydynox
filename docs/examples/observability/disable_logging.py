import logging

from pydynox import DynamoDBClient

# Disable pydynox logs completely
logging.getLogger("pydynox").setLevel(logging.CRITICAL)

client = DynamoDBClient()

# No logs will be emitted
client.put_item("users", {"pk": "USER#1", "sk": "PROFILE", "name": "John"})
client.get_item("users", {"pk": "USER#1", "sk": "PROFILE"})
