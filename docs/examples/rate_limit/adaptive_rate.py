from pydynox import DynamoDBClient
from pydynox.rate_limit import AdaptiveRate

# Set max capacity, it figures out the rest
client = DynamoDBClient(rate_limit=AdaptiveRate(max_rcu=100))

# With write limit too
client = DynamoDBClient(rate_limit=AdaptiveRate(max_rcu=100, max_wcu=50))

# With custom min (won't go below this)
client = DynamoDBClient(rate_limit=AdaptiveRate(max_rcu=100, min_rcu=10))
