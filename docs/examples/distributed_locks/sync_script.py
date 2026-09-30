"""A sync section with a transaction ownership check."""

from pydynox import DynamoDBClient
from pydynox.lock import SyncDistributedLock
from pydynox.transaction import SyncTransaction

client = DynamoDBClient()
for table, partition_key in (("script_locks", "key"), ("import_results", "job_id")):
    if not client.sync_table_exists(table):
        client.sync_create_table(table, partition_key=(partition_key, "S"), wait=True)

with SyncDistributedLock(client, table="script_locks", key="import:daily") as lease:
    summary = "Imported 100 rows"
    with SyncTransaction(client) as transaction:
        lease.check_in(transaction)
        transaction.put("import_results", {"job_id": "daily", "summary": summary})

assert lease.metrics.write_requests == 2
assert client.sync_get_item("import_results", {"job_id": "daily"})["summary"] == summary
