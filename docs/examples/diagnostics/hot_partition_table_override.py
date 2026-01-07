"""Override thresholds for specific tables."""

from pydynox import DynamoDBClient
from pydynox.diagnostics import HotPartitionDetector

detector = HotPartitionDetector(
    writes_threshold=500,
    reads_threshold=1500,
    window_seconds=60,
)

# High-traffic table needs higher threshold
detector.set_table_thresholds(
    "events",
    writes_threshold=2000,
    reads_threshold=5000,
)

# Cache table has lots of reads
detector.set_table_thresholds(
    "config_cache",
    reads_threshold=10000,
)

client = DynamoDBClient(
    region="us-east-1",
    diagnostics=detector,
)
