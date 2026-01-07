"""Basic hot partition detection setup."""

from pydynox import DynamoDBClient
from pydynox.diagnostics import HotPartitionDetector

# Create detector with thresholds
detector = HotPartitionDetector(
    writes_threshold=500,  # Warn after 500 writes per partition
    reads_threshold=1500,  # Warn after 1500 reads per partition
    window_seconds=60,  # Count operations in 60-second window
)

# Pass detector to client
client = DynamoDBClient(
    region="us-east-1",
    diagnostics=detector,
)

# Now all operations are tracked
# If a partition gets too hot, you'll see a warning in logs:
# WARNING: Hot partition detected - table="events" pk="EVENTS" had 500 writes in 60s
