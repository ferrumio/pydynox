from pydynox import DynamoDBClient

# Use an HTTP/HTTPS proxy
client = DynamoDBClient(
    proxy_url="http://proxy.example.com:8080",
)

# With authentication
client = DynamoDBClient(
    proxy_url="http://user:password@proxy.example.com:8080",
)
