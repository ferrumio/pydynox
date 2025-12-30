"""Client with rate limiting."""

from pydynox import DynamoDBClient
from pydynox.rate_limit import AdaptiveRate, FixedRate

# Fixed rate: constant throughput
client = DynamoDBClient(
    rate_limit=FixedRate(rcu=50, wcu=25),
)

# Adaptive rate: adjusts based on throttling
client = DynamoDBClient(
    rate_limit=AdaptiveRate(max_rcu=100, max_wcu=50),
)
