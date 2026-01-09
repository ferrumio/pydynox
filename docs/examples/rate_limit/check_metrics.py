from pydynox import DynamoDBClient
from pydynox.rate_limit import FixedRate

rate_limit = FixedRate(rcu=50, wcu=25)
client = DynamoDBClient(rate_limit=rate_limit)

# After some operations...
for i in range(10):
    client.put_item("users", {"pk": f"USER#RATE{i}", "sk": "PROFILE", "name": f"User {i}"})

# Check metrics
print(f"RCU used: {rate_limit.consumed_rcu}")
print(f"WCU used: {rate_limit.consumed_wcu}")
print(f"Throttle count: {rate_limit.throttle_count}")
