from pydynox import Model
from pydynox.attributes import CompressedAttribute, StringAttribute


class LogEntry(Model):
    class Meta:
        table = "logs"

    pk = StringAttribute(hash_key=True)

    # Custom compression settings
    message = CompressedAttribute(
        level=10,  # Higher level = better compression, slower
        min_size=200,  # Only compress if >= 200 bytes
        threshold=0.8,  # Only compress if saves at least 20%
    )
