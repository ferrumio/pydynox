from pydynox import DynamoDBClient
from pydynox.rate_limit import FixedRate

# Limit to 50 read capacity units per second
client = DynamoDBClient(rate_limit=FixedRate(rcu=50))

# Limit both read and write
client = DynamoDBClient(rate_limit=FixedRate(rcu=50, wcu=25))

# Allow bursts up to 200 RCU
client = DynamoDBClient(rate_limit=FixedRate(rcu=50, burst=200))
