from pydynox import Model, ModelConfig
from pydynox.attributes import CompressedAttribute, StringAttribute


class LogEntry(Model):
    model_config = ModelConfig(table="logs")

    pk = StringAttribute(partition_key=True)

    # Custom compression settings
    message = CompressedAttribute(
        level=10,  # Higher level = better compression, slower
        min_size=200,  # Only compress if >= 200 bytes
        threshold=0.8,  # Only compress if saves at least 20%
    )
