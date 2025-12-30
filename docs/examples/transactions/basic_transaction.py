from pydynox import DynamoDBClient, Transaction

client = DynamoDBClient()

# All operations succeed or fail together
with Transaction(client) as tx:
    tx.put("users", {"pk": "USER#1", "name": "John"})
    tx.put("orders", {"pk": "ORDER#1", "user": "USER#1"})
    tx.delete("temp", {"pk": "TEMP#1"})
