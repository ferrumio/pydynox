from pydynox import DynamoDBClient, Transaction

client = DynamoDBClient()

# All operations succeed or fail together
with Transaction(client) as tx:
    tx.put("users", {"pk": "USER#TX1", "sk": "PROFILE", "name": "John"})
    tx.put("orders", {"pk": "ORDER#TX1", "sk": "DETAILS", "user": "USER#TX1"})
    tx.delete("temp", {"pk": "TEMP#1"})
