"""Override thresholds per model using ModelConfig."""

from pydynox import DynamoDBClient, Model, ModelConfig, set_default_client
from pydynox.attributes import StringAttribute
from pydynox.diagnostics import HotPartitionDetector

detector = HotPartitionDetector(
    writes_threshold=500,
    reads_threshold=1500,
    window_seconds=60,
)

client = DynamoDBClient(
    region="us-east-1",
    diagnostics=detector,
)
set_default_client(client)


# Normal model uses client's default thresholds
class User(Model):
    model_config = ModelConfig(table="users")
    pk = StringAttribute(hash_key=True)
    name = StringAttribute()


# High-traffic model overrides thresholds
class Event(Model):
    model_config = ModelConfig(
        table="events",
        hot_partition_writes=2000,  # Override client's 500
        hot_partition_reads=5000,  # Override client's 1500
    )
    pk = StringAttribute(hash_key=True)
    event_type = StringAttribute()
