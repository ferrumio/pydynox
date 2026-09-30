"""Real AWS SDK requests against LocalStack, including process failure."""

import asyncio
import multiprocessing
import os
import signal
import subprocess
import sys
import time
from collections import Counter
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Event, Thread
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from uuid import uuid4

import pytest
from pydynox import DynamoDBClient
from pydynox.exceptions import (
    LockLost,
    LockNotAcquired,
    ResourceNotFoundException,
    TransactionCanceledException,
)
from pydynox.lock import DistributedLock, SyncDistributedLock, distributed_lock
from pydynox.transaction import SyncTransaction, Transaction


def make_client(endpoint):
    return DynamoDBClient(
        region="us-east-1",
        access_key="testing",
        secret_key="testing",
        endpoint_url=endpoint,
    )


@pytest.fixture(scope="module")
def lock_table(localstack_endpoint):
    client = make_client(localstack_endpoint)
    table = f"locks-{uuid4().hex}"
    client.sync_create_table(table, partition_key=("key", "S"), wait=True)
    yield table
    client.sync_delete_table(table)


@pytest.fixture
def lock_key():
    return uuid4().hex


def test_native_acquire_renew_release(localstack_endpoint, lock_table, lock_key):
    # GIVEN two independent SDK clients
    client = make_client(localstack_endpoint)
    contender = make_client(localstack_endpoint)
    lease = SyncDistributedLock(client, table=lock_table, key=lock_key, lease_duration=1.5)
    with lease:
        original = client.sync_get_item(lock_table, {"key": lock_key}, consistent_read=True)
        deadline = time.monotonic() + 4
        while lease.metrics.renewals < 2 and time.monotonic() < deadline:
            time.sleep(0.01)
        lease.raise_if_lost()
        assert lease.metrics.renewals >= 2
        current = client.sync_get_item(lock_table, {"key": lock_key}, consistent_read=True)
        assert current["owner"] == original["owner"]
        assert current["version"] != original["version"]
        with pytest.raises(LockNotAcquired):
            with SyncDistributedLock(contender, table=lock_table, key=lock_key, wait_timeout=0):
                pytest.fail("A second client stole a renewing lock")
    assert client.sync_get_item(lock_table, {"key": lock_key}) is None
    assert lease.metrics.write_requests == lease.metrics.renewals + 2
    assert lease.metrics.consumed_wcu > 0


async def test_native_decorator_contenders(localstack_endpoint, lock_table):
    client = make_client(localstack_endpoint)
    active = set()
    max_active = 0

    @distributed_lock(client, table=lock_table, key="{key}", lease_duration=1.5, wait_timeout=8)
    async def work(key):
        nonlocal max_active
        assert key not in active
        active.add(key)
        max_active = max(max_active, len(active))
        await asyncio.sleep(0.02)
        active.remove(key)
        return key

    a, b = uuid4().hex, uuid4().hex
    keys = [a, b, a, b, a, b]
    assert await asyncio.gather(*(work(key) for key in keys)) == keys
    assert max_active == 2


@pytest.mark.parametrize("wait", [0, 0.05])
def test_native_short_retry_recovery(localstack_endpoint, lock_table, lock_key, wait):
    client = make_client(localstack_endpoint)
    client.sync_put_item(
        lock_table,
        {"key": lock_key, "owner": "dead", "version": "old", "lease_ms": 300, "protocol": 1},
    )
    for _ in range(2):
        # Each fresh client loses observation history and cannot skip expiry.
        with pytest.raises(LockNotAcquired):
            with SyncDistributedLock(
                make_client(localstack_endpoint),
                table=lock_table,
                key=lock_key,
                wait_timeout=wait,
            ):
                pass
    with pytest.raises(LockNotAcquired):
        with SyncDistributedLock(client, table=lock_table, key=lock_key, wait_timeout=wait):
            pass
    time.sleep(0.35)
    with SyncDistributedLock(client, table=lock_table, key=lock_key, wait_timeout=wait):
        assert client.sync_get_item(lock_table, {"key": lock_key})["owner"] != "dead"


def test_native_stale_transaction_rejected(table, lock_table, lock_key):
    with SyncDistributedLock(table, table=lock_table, key=lock_key) as lease:
        with SyncTransaction(table) as transaction:
            lease.check_in(transaction)
            transaction.put("test_table", {"pk": lock_key, "sk": "value", "n": 1})
        stale = SyncTransaction(table)
        lease.check_in(stale)
        stale.put("test_table", {"pk": lock_key, "sk": "value", "n": 2})
    # The old check cannot authorize a write after release and reacquisition.
    with SyncDistributedLock(table, table=lock_table, key=lock_key):
        with pytest.raises(TransactionCanceledException):
            stale.commit()
    assert table.sync_get_item("test_table", {"pk": lock_key, "sk": "value"})["n"] == 1


async def test_native_async_transaction(table, lock_table, lock_key):
    async with DistributedLock(table, table=lock_table, key=lock_key) as lease:
        async with Transaction(table) as transaction:
            lease.check_in(transaction)
            transaction.put("test_table", {"pk": lock_key, "sk": "value"})
    assert await table.get_item("test_table", {"pk": lock_key, "sk": "value"})


def owner_process(endpoint, table, key, channel):
    """Spawn a separate interpreter so renewal stops with the process."""
    client = make_client(endpoint)
    try:
        with SyncDistributedLock(client, table=table, key=key, lease_duration=1.5) as lease:
            pending = SyncTransaction(client)
            lease.check_in(pending)
            pending.put(table, {"key": f"result-{key}", "value": "stale"})
            channel.send("held")
            channel.recv()
            try:
                lease.raise_if_lost()
            except LockLost:
                channel.send("lost")
            else:
                channel.send("still-held")
            try:
                pending.commit()
            except TransactionCanceledException:
                channel.send("stale-write-rejected")
            else:
                channel.send("stale-write-accepted")
    except LockLost:
        channel.send("release-rejected")
    finally:
        channel.close()


@pytest.mark.skipif(os.name != "posix", reason="Uses process pause/kill signals")
@pytest.mark.parametrize("failure", ["kill", "pause"])
def test_process_failure_and_stale_owner(localstack_endpoint, lock_table, lock_key, failure):
    context = multiprocessing.get_context("spawn")
    parent, child = context.Pipe()
    worker = context.Process(
        target=owner_process, args=(localstack_endpoint, lock_table, lock_key, child)
    )
    worker.start()
    child.close()
    try:
        assert parent.poll(10)
        assert parent.recv() == "held"
        os.kill(worker.pid, signal.SIGKILL if failure == "kill" else signal.SIGSTOP)
        client = make_client(localstack_endpoint)
        start = time.monotonic()
        with SyncDistributedLock(
            client, table=lock_table, key=lock_key, lease_duration=1.5, wait_timeout=6
        ) as successor:
            # A fresh observer waits the previous owner's full stored lease.
            assert time.monotonic() - start >= 1.5
            if failure == "pause":
                os.kill(worker.pid, signal.SIGCONT)
                parent.send("resume")
                for expected in ("lost", "stale-write-rejected", "release-rejected"):
                    assert parent.poll(5)
                    assert parent.recv() == expected
                assert client.sync_get_item(lock_table, {"key": f"result-{lock_key}"}) is None
            successor.raise_if_lost()
            assert client.sync_get_item(lock_table, {"key": lock_key}) is not None
    finally:
        if worker.is_alive():
            worker.kill()
        worker.join(5)
        parent.close()
        assert not worker.is_alive()


def test_multiple_processes_take_over_one_abandoned_row(localstack_endpoint, lock_table, lock_key):
    # Atomic destination updates serve as an independent overlap detector.
    client = make_client(localstack_endpoint)
    client.sync_put_item(
        lock_table,
        {"key": lock_key, "owner": "dead", "version": "old", "lease_ms": 300, "protocol": 1},
    )
    context = multiprocessing.get_context("spawn")
    results = context.Queue()
    start = context.Event()
    workers = [
        context.Process(
            target=contender_process,
            args=(localstack_endpoint, lock_table, lock_key, start, results),
        )
        for _ in range(4)
    ]
    for worker in workers:
        worker.start()
    start.set()
    try:
        messages = [results.get(timeout=15) for _ in workers]
        assert all(message == "ok" for message in messages), messages
    finally:
        for worker in workers:
            worker.join(3)
            if worker.is_alive():
                worker.kill()
                worker.join(3)
        results.close()


def contender_process(endpoint, table, key, start, results):
    client = make_client(endpoint)
    start.wait(10)
    try:
        with SyncDistributedLock(
            client, table=table, key=key, lease_duration=1.5, wait_timeout=10
        ) as lease:
            with SyncTransaction(client) as transaction:
                lease.check_in(transaction)
                transaction.put(
                    table, {"key": f"active-{key}"}, "attribute_not_exists(#key)", {"#key": "key"}
                )
            time.sleep(0.025)
            with SyncTransaction(client) as transaction:
                lease.check_in(transaction)
                transaction.delete(table, {"key": f"active-{key}"})
        results.put("ok")
    except BaseException as error:
        results.put(repr(error))


@contextmanager
def fault_proxy(upstream, target, mode):
    """Delay or drop responses while preserving actual DynamoDB writes."""
    triggered = Event()
    committed = Event()
    allow = Event()
    counts = Counter()

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_POST(self):
            operation = self.headers["X-Amz-Target"].rsplit(".", 1)[-1]
            counts[operation] += 1
            body = self.rfile.read(int(self.headers["Content-Length"]))
            inject = operation == target and not triggered.is_set()
            if mode == "partition" and operation in {"GetItem", "UpdateItem"}:
                self.send_response(503)
                self.end_headers()
                self.wfile.write(b'{"__type":"ServiceUnavailable","message":"partition"}')
                return
            if inject:
                triggered.set()
                if mode == "late_commit":
                    allow.wait(5)
            headers = {
                key: value
                for key, value in self.headers.items()
                if key.lower() not in {"host", "content-length", "connection"}
            }
            request = Request(upstream, data=body, headers=headers, method="POST")
            try:
                response = urlopen(request, timeout=5)
            except HTTPError as error:
                response = error
            with response:
                payload = response.read()
                status = response.status
            if inject:
                committed.set()
                if mode == "lost_response":
                    # Native per-request timeout is 0.4s for these tests.
                    time.sleep(0.55)
            try:
                self.send_response(status)
                self.send_header("Content-Type", "application/x-amz-json-1.0")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)
            except (BrokenPipeError, ConnectionResetError):
                pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}", triggered, committed, allow, counts
    finally:
        allow.set()
        server.shutdown()
        server.server_close()
        thread.join(3)


@pytest.mark.parametrize("operation", ["PutItem", "UpdateItem", "DeleteItem"])
def test_native_http_timeout_after_commit(localstack_endpoint, lock_table, lock_key, operation):
    with fault_proxy(localstack_endpoint, operation, "lost_response") as proxy:
        endpoint, triggered, committed, _, counts = proxy
        client = make_client(endpoint)
        with SyncDistributedLock(
            client, table=lock_table, key=lock_key, lease_duration=1.2
        ) as lease:
            if operation == "UpdateItem":
                deadline = time.monotonic() + 3
                while lease.metrics.renewals < 1 and time.monotonic() < deadline:
                    time.sleep(0.01)
                assert lease.metrics.renewals >= 1
            lease.raise_if_lost()
        assert triggered.is_set() and committed.is_set()
        assert counts["GetItem"] >= 1
        assert lease.metrics.request_failures == 1
        assert not lease.metrics.lost
        assert make_client(localstack_endpoint).sync_get_item(lock_table, {"key": lock_key}) is None


async def test_remote_acquisition_after_cancellation_never_renews(
    localstack_endpoint, lock_table, lock_key
):
    with fault_proxy(localstack_endpoint, "PutItem", "late_commit") as proxy:
        endpoint, triggered, committed, allow, counts = proxy
        client = make_client(endpoint)
        lease = DistributedLock(client, table=lock_table, key=lock_key, lease_duration=1.2)
        entered = False

        async def work():
            nonlocal entered
            async with lease:
                entered = True

        task = asyncio.create_task(work())
        assert await asyncio.to_thread(triggered.wait, 3)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        # Let conditional cleanup finish before the delayed put reaches DynamoDB.
        deadline = time.monotonic() + 3
        while counts["DeleteItem"] == 0 and time.monotonic() < deadline:
            await asyncio.sleep(0.01)
        assert counts["DeleteItem"] == 1
        await asyncio.sleep(0.05)
        allow.set()
        assert await asyncio.to_thread(committed.wait, 3)
        await asyncio.sleep(0.5)
        assert not entered
        assert counts["UpdateItem"] == 0
        with pytest.raises(LockLost):
            lease.raise_if_lost()
        # A late remote commit can leave an abandoned row, but it is recoverable.
        async with DistributedLock(
            make_client(localstack_endpoint),
            table=lock_table,
            key=lock_key,
            lease_duration=1.2,
            wait_timeout=4,
        ):
            pass


def test_native_partition_stops_renewing(localstack_endpoint, lock_table, lock_key):
    with fault_proxy(localstack_endpoint, "UpdateItem", "partition") as proxy:
        endpoint, _, _, _, counts = proxy
        lease = SyncDistributedLock(
            make_client(endpoint), table=lock_table, key=lock_key, lease_duration=1.2
        )
        with pytest.raises(LockLost):
            with lease:
                deadline = time.monotonic() + 3
                while not lease.metrics.lost and time.monotonic() < deadline:
                    time.sleep(0.01)
                assert lease.metrics.lost
                assert lease.metrics.renewals == 0
        writes = counts["UpdateItem"]
        time.sleep(0.45)
        assert counts["UpdateItem"] == writes


async def test_cancel_during_release_finishes_cleanup(localstack_endpoint, lock_table, lock_key):
    with fault_proxy(localstack_endpoint, "DeleteItem", "lost_response") as proxy:
        endpoint, triggered, _, _, counts = proxy
        lease = DistributedLock(
            make_client(endpoint), table=lock_table, key=lock_key, lease_duration=1.2
        )

        async def work():
            async with lease:
                pass

        task = asyncio.create_task(work())
        assert await asyncio.to_thread(triggered.wait, 3)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        await asyncio.sleep(0.8)
        assert counts["DeleteItem"] == 1
        assert counts["UpdateItem"] == 0
        assert counts["GetItem"] >= 1
        assert make_client(localstack_endpoint).sync_get_item(lock_table, {"key": lock_key}) is None


async def test_release_waits_for_renewal_and_does_not_recreate_row(
    localstack_endpoint, lock_table, lock_key
):
    with fault_proxy(localstack_endpoint, "UpdateItem", "lost_response") as proxy:
        endpoint, triggered, _, _, counts = proxy
        lease = DistributedLock(
            make_client(endpoint), table=lock_table, key=lock_key, lease_duration=1.2
        )
        async with lease:
            assert await asyncio.to_thread(triggered.wait, 3)
            started = time.monotonic()
        assert time.monotonic() - started < 0.9
        await asyncio.sleep(0.6)
        assert counts["UpdateItem"] == 1
        assert counts["DeleteItem"] == 1
        assert make_client(localstack_endpoint).sync_get_item(lock_table, {"key": lock_key}) is None


def test_missing_table_is_not_contention(localstack_endpoint):
    with pytest.raises(ResourceNotFoundException):
        with SyncDistributedLock(
            make_client(localstack_endpoint), table=f"missing-{uuid4().hex}", key="work"
        ):
            pytest.fail("A missing table must not enter the protected block")


@pytest.mark.skipif(os.name != "posix", reason="Tests fork inheritance")
def test_inherited_client_guard_and_metrics_fail_before_runtime_use():
    # Isolate fork from pytest's event loop and other test fixtures.
    script = """
import os
from pydynox import DynamoDBClient
from pydynox.lock import SyncDistributedLock
client = DynamoDBClient(region="us-east-1", access_key="testing", secret_key="testing")
lease = SyncDistributedLock(client, table="locks", key="work")
pid = os.fork()
if pid == 0:
    checks = [
        lambda: SyncDistributedLock(client, table="locks", key="other"),
        lease.__enter__,
        lease.raise_if_lost,
        lambda: lease.metrics,
    ]
    for check in checks:
        try:
            check()
        except RuntimeError:
            continue
        os._exit(1)
    os._exit(0)
_, status = os.waitpid(pid, 0)
raise SystemExit(os.waitstatus_to_exitcode(status))
"""
    result = subprocess.run(
        [sys.executable, "-c", script], capture_output=True, text=True, timeout=10
    )
    assert result.returncode == 0, result.stderr
