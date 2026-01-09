from aws_lambda_powertools import Logger
from pydynox import DynamoDBClient, set_logger

# With AWS Lambda Powertools
logger = Logger()
set_logger(logger)

# Now all pydynox logs go through Powertools
client = DynamoDBClient()
client.put_item("users", {"pk": "USER#1", "sk": "PROFILE", "name": "John"})
