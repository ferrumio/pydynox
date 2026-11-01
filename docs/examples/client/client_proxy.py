from pydynox import DynamoDBClient

# Use an HTTP/HTTPS proxy (configured on this client's HTTP transport only —
# it does not mutate process-wide HTTPS_PROXY / HTTP_PROXY).
client = DynamoDBClient(
    proxy_url="http://proxy.example.com:8080",
)

# With authentication
client = DynamoDBClient(
    proxy_url="http://user:password@proxy.example.com:8080",
)
