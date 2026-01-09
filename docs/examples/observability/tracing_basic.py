"""Basic OpenTelemetry tracing example."""

from pydynox import DynamoDBClient, Model, ModelConfig, enable_tracing
from pydynox.attributes import StringAttribute

# Enable tracing - uses global OTEL tracer
enable_tracing()

client = DynamoDBClient(region="us-east-1")


class User(Model):
    model_config = ModelConfig(table="users", client=client)
    pk = StringAttribute(hash_key=True)
    sk = StringAttribute(range_key=True)
    name = StringAttribute()


# All operations now create spans automatically
user = User(pk="USER#123", sk="PROFILE", name="John")
user.save()  # Span: "PutItem users"

result = User.get(pk="USER#123", sk="PROFILE")  # Span: "GetItem users"
