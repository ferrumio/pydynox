"""Public API and fault tests using the native protocol with MemoryBackend."""

import asyncio
import inspect
import random
import time
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier, Event, Lock

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from pydynox.exceptions import (
    AccessDeniedException,
    ConnectionException,
    LockLost,
    LockNotAcquired,
    LockReleaseError,
    ResourceNotFoundException,
    ValidationException,
)
from pydynox.lock import DistributedLock, SyncDistributedLock, distributed_lock
from pydynox.testing import MemoryBackend
from pydynox.transaction import SyncTransaction


@pytest.fixture
def locks():
    with MemoryBackend() as backend:
        backend.client.sync_create_table("locks", partition_key=("key", "S"))
        yield backend.client


def guard(client, key="work", **kwargs):
    return SyncDistributedLock(client, table="locks", key=key, **kwargs)


def stored(client, key="work"):
    return client.sync_get_item("locks", {"key": key})


def abandoned(client, lease_ms=150, **overrides):
    row = {
        "key": "work",
        "owner": "former-owner",
        "version": "unchanged",
        "lease_ms": lease_ms,
        "protocol": 1,
        **overrides,
    }
    client.sync_put_item("locks", row)
    return row


def eventually(predicate, timeout=2):
    deadline = time.monotonic() + timeout
    while not predicate():
        if time.monotonic() >= deadline:
            pytest.fail("Condition did not become true before the test deadline")
        time.sleep(0.005)


def test_short_lock_cost_and_single_use(locks):
    # GIVEN a fresh guard with no contender
    lease = guard(locks)
    with pytest.raises(LockLost):
        lease.raise_if_lost()

    # WHEN it completes before the first renewal
    with lease:
        first_owner = stored(locks)["owner"]
        lease.raise_if_lost()
        before_release = lease.metrics
        with pytest.raises(RuntimeError, match="single-use"):
            lease.__enter__()
        lease.raise_if_lost()

    # THEN acquire + release cost two requests and a snapshot stays unchanged
    assert stored(locks) is None
    assert before_release.write_requests == 1
    assert lease.metrics.write_requests == 2
    assert lease.metrics.read_requests == 0
    assert lease.metrics.renewals == 0
    with pytest.raises(RuntimeError, match="single-use"):
        lease.__enter__()
    with pytest.raises(LockLost):
        lease.raise_if_lost()
    with guard(locks):
        assert stored(locks)["owner"] != first_owner


async def test_async_lock_and_event_loop_reuse(locks):
    # GIVEN the async API backed by the same native state machine
    lease = DistributedLock(locks, table="locks", key="work")
    async with lease:
        with pytest.raises(RuntimeError, match="single-use"):
            await lease.__aenter__()
        lease.raise_if_lost()
    assert stored(locks) is None
    assert lease.metrics.write_requests == 2


def test_client_can_be_reused_across_event_loops(locks):
    async def run():
        async with DistributedLock(locks, table="locks", key="work"):
            assert stored(locks) is not None

    asyncio.run(run())
    asyncio.run(run())
    assert stored(locks) is None


@pytest.mark.parametrize("wait", [0, 0.04])
def test_nested_same_key_obeys_wait_budget(locks, wait):
    with guard(locks, lease_duration=0.6) as owner:
        contender = guard(locks, lease_duration=0.6, wait_timeout=wait)
        start = time.monotonic()
        with pytest.raises(LockNotAcquired):
            contender.__enter__()
        assert time.monotonic() - start < 0.3
        assert contender.metrics.conditional_failures == 1
        assert contender.metrics.wait_timeouts == 1
        assert contender.metrics.wait_ms > 0
        owner.raise_if_lost()
        # Independent keys can acquire while the first remains held.
        with guard(locks, key="other"):
            pass


def test_renewal_outlives_several_lease_windows(locks):
    with guard(locks, lease_duration=0.3) as lease:
        original = stored(locks)
        eventually(lambda: lease.metrics.renewals >= 4)
        lease.raise_if_lost()
        current = stored(locks)
        assert current["owner"] == original["owner"]
        assert current["version"] != original["version"]
        with pytest.raises(LockNotAcquired):
            with guard(locks, lease_duration=0.1, wait_timeout=0):
                pytest.fail("A renewing owner must not be stolen")
    assert lease.metrics.write_requests == lease.metrics.renewals + 2
    writes = lease.metrics.write_requests
    time.sleep(0.15)
    assert lease.metrics.write_requests == writes
    assert stored(locks) is None


@pytest.mark.parametrize("wait", [0, 0.015])
def test_short_retries_retain_observations(locks, wait):
    # GIVEN an abandoned owner whose lease is longer than each caller's wait
    abandoned(locks, lease_ms=180)
    with pytest.raises(LockNotAcquired):
        with guard(locks, lease_duration=0.1, wait_timeout=wait):
            pass
    time.sleep(0.2)

    # WHEN the same client retries, its original observation permits takeover
    with guard(locks, lease_duration=0.1, wait_timeout=wait):
        assert stored(locks)["owner"] != "former-owner"


def test_fresh_clients_cannot_skip_observation_or_stored_lease(locks):
    # GIVEN a stored lease much longer than the contender's own lease
    original = abandoned(locks, lease_ms=400)
    start = time.monotonic()
    with pytest.raises(LockNotAcquired):
        with guard(locks, lease_duration=0.1, wait_timeout=0.18):
            pass
    assert time.monotonic() - start < 0.35
    assert stored(locks) == original

    # A new client needs its own observation, even if the row is old.
    with MemoryBackend() as fresh:
        fresh.client.sync_create_table("locks", partition_key=("key", "S"))
        fresh.client.sync_put_item("locks", original)
        with pytest.raises(LockNotAcquired):
            with guard(fresh.client, lease_duration=0.1, wait_timeout=0):
                pass


def test_changed_version_restarts_observation(locks):
    abandoned(locks)
    with pytest.raises(LockNotAcquired):
        with guard(locks, wait_timeout=0):
            pass
    time.sleep(0.17)
    abandoned(locks, version="new-version")
    with pytest.raises(LockNotAcquired):
        with guard(locks, wait_timeout=0):
            pass


@pytest.mark.parametrize(
    "overrides",
    [
        {"protocol": 2},
        {"lease_ms": 0},
        {"lease_ms": 99},
        {"lease_ms": 86_400_001},
        {"lease_ms": "30000"},
        {"owner": ""},
        {"version": 123},
    ],
)
def test_unknown_or_malformed_rows_are_not_stolen(locks, overrides):
    row = abandoned(locks, **overrides)
    with pytest.raises(ValueError, match="lock record"):
        with guard(locks, wait_timeout=0):
            pass
    assert stored(locks) == row


@pytest.mark.parametrize(
    "kwargs",
    [
        {"key": ""},
        {"key": "é" * 1025},
        {"lease_duration": 0},
        {"lease_duration": -1},
        {"lease_duration": float("nan")},
        {"lease_duration": float("inf")},
        {"lease_duration": 86401},
        {"wait_timeout": -1},
        {"wait_timeout": float("nan")},
    ],
)
def test_invalid_inputs_fail_before_io(locks, kwargs):
    with pytest.raises(ValueError):
        guard(locks, **kwargs)
    assert not locks._tables["locks"]


def test_sync_contenders_do_not_overlap(locks):
    barrier = Barrier(6)
    mutex = Lock()
    active = 0
    owners = set()

    def worker():
        nonlocal active
        barrier.wait(timeout=5)
        with guard(locks, lease_duration=0.6, wait_timeout=3):
            with mutex:
                active += 1
                assert active == 1
                owners.add(stored(locks)["owner"])
            time.sleep(0.015)
            with mutex:
                active -= 1

    with ThreadPoolExecutor(max_workers=6) as executor:
        list(executor.map(lambda _: worker(), range(6)))
    assert len(owners) == 6
    assert stored(locks) is None


async def test_async_contenders_and_independent_keys(locks):
    active = set()
    max_active = 0

    @distributed_lock(locks, table="locks", key="{key}", lease_duration=0.6, wait_timeout=3)
    async def worker(key):
        nonlocal max_active
        assert key not in active
        active.add(key)
        max_active = max(max_active, len(active))
        await asyncio.sleep(0.01)
        active.remove(key)
        return key

    keys = ["a", "b", "a", "b", "a", "b"]
    assert await asyncio.gather(*(worker(key) for key in keys)) == keys
    assert max_active == 2


@pytest.mark.parametrize("call", [lambda f: f("123"), lambda f: f(customer="123"), lambda f: f()])
def test_decorator_signature_defaults_and_no_setup_io(locks, call):
    @distributed_lock(locks, table="locks", key="customer:{customer}")
    def work(customer="123", *, option=True):
        """Business documentation."""
        assert stored(locks, "customer:123") is not None
        return customer, option

    assert not locks._tables["locks"]
    assert inspect.signature(work) == inspect.signature(work.__wrapped__)
    assert work.__doc__ == "Business documentation."
    assert call(work) == ("123", True)
    assert stored(locks, "customer:123") is None


def test_method_binding_positional_only_and_variadic_arguments(locks):
    class Worker:
        @distributed_lock(locks, table="locks", key="{customer}:{job}")
        def work(self, customer, /, *args, job="sync", **kwargs):
            return customer, args, job, kwargs, stored(locks, "3:abc:4:sync")

    result = Worker().work("abc", 7, customer="different")
    assert result[:4] == ("abc", (7,), "sync", {"customer": "different"})
    assert result[4] is not None


@pytest.mark.parametrize(
    "key", ["{missing}", "{customer", "customer}", "{customer.attr}", "{args}"]
)
def test_invalid_templates_fail_at_decoration(locks, key):
    with pytest.raises(ValueError):
        distributed_lock(locks, table="locks", key=key)(lambda customer, *args: None)
    assert not locks._tables["locks"]


@pytest.mark.parametrize(
    "call",
    [
        lambda f: f(),
        lambda f: f(123),
        lambda f: f("a", customer="b"),
        lambda f: f("a", "b"),
        lambda f: f("a", unknown=True),
    ],
)
def test_invalid_call_never_acquires_or_enters_body(locks, call):
    @distributed_lock(locks, table="locks", key="{customer}")
    def work(customer):
        pytest.fail("Invalid call entered the body")

    with pytest.raises(TypeError):
        call(work)
    assert not locks._tables["locks"]


def test_key_values_do_not_collide(locks):
    resolved = []

    @distributed_lock(locks, table="locks", key="{left}:{right}")
    def work(left, right):
        resolved.extend(item["key"] for item in locks._tables["locks"].values())

    work("a:b", "c")
    work("a", "b:c")
    assert resolved == ["3:a:b:1:c", "1:a:3:b:c"]

    @distributed_lock(locks, table="locks", key="{{literal}}")
    def literal():
        assert stored(locks, "{literal}") is not None

    literal()


def test_generators_rejected(locks):
    def generator():
        yield 1

    async def async_generator():
        yield 1

    for function in (generator, async_generator):
        with pytest.raises(TypeError, match="generator"):
            distributed_lock(locks, table="locks", key="work")(function)


async def test_unawaited_coroutine_does_not_acquire(locks):
    @distributed_lock(locks, table="locks", key="work")
    async def work():
        return 42

    coroutine = work()
    assert stored(locks) is None
    coroutine.close()
    assert await work() == 42


async def test_cancelled_body_preserves_cancellation_and_releases(locks):
    entered = asyncio.Event()

    @distributed_lock(locks, table="locks", key="work")
    async def work():
        entered.set()
        await asyncio.sleep(60)

    task = asyncio.create_task(work())
    await entered.wait()
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert stored(locks) is None


async def test_cancelled_contender_does_not_release_owner(locks):
    with guard(locks) as owner:
        contender = DistributedLock(locks, table="locks", key="work", wait_timeout=5)
        task = asyncio.create_task(contender.__aenter__())
        while contender.metrics.read_requests == 0:
            await asyncio.sleep(0.005)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        owner.raise_if_lost()
        assert contender.metrics.write_requests == 1
        assert stored(locks) is not None


@pytest.mark.parametrize("operation", ["acquire", "renew", "release"])
def test_committed_write_with_lost_response_is_reconciled(locks, monkeypatch, operation):
    # GIVEN a storage operation that commits once but loses its response
    method = "_lock_delete" if operation == "release" else "_lock_put"
    original = getattr(locks, method)
    injected = Event()

    def faulty(*args):
        original(*args)
        is_target = operation != "renew" or args[2] is not None
        if is_target and not injected.is_set():
            injected.set()
            raise ConnectionException("Response lost after commit")

    monkeypatch.setattr(locks, method, faulty)
    with guard(locks, lease_duration=0.6) as lease:
        if operation == "renew":
            eventually(lambda: lease.metrics.renewals >= 1)
        lease.raise_if_lost()
    assert injected.is_set()
    assert lease.metrics.request_failures == 1
    assert lease.metrics.read_requests >= 1
    assert not lease.metrics.lost
    assert stored(locks) is None


def test_acquisition_failure_does_not_run_body(locks, monkeypatch):
    def denied(*args):
        raise AccessDeniedException("Denied")

    monkeypatch.setattr(locks, "_lock_put", denied)
    with pytest.raises(AccessDeniedException):
        with guard(locks):
            pytest.fail("An unconfirmed acquisition entered the body")


@pytest.mark.parametrize("body_fails", [False, True])
def test_unconfirmed_release_is_visible_without_masking_body(locks, monkeypatch, body_fails):
    def unavailable(*args):
        raise ConnectionException("Disconnected")

    monkeypatch.setattr(locks, "_lock_delete", unavailable)
    expected = ValueError if body_fails else LockReleaseError
    with pytest.raises(expected) as error:
        with guard(locks) as lease:
            if body_fails:
                raise ValueError("Business failure")
    assert stored(locks) is not None
    assert lease.metrics.cleanup_failures == 1
    if body_fails:
        assert str(error.value) == "Business failure"
        assert "cleanup" in error.value.__notes__[0]
    writes = lease.metrics.write_requests
    time.sleep(0.05)
    assert lease.metrics.write_requests == writes


def test_lost_owner_cannot_renew_or_release_successor(locks):
    with pytest.raises(LockLost):
        with guard(locks, lease_duration=0.3) as lease:
            successor = abandoned(locks, owner="successor")
            eventually(lambda: lease.metrics.lost)
            with pytest.raises(LockLost):
                lease.raise_if_lost()
            assert stored(locks) == successor
    assert stored(locks) == successor


def test_network_partition_expires_owner_and_stops_renewal(locks, monkeypatch):
    original = locks._lock_put

    def partition(table, item, owner, version):
        if owner is not None:
            raise ConnectionException("Renewal partition")
        return original(table, item, owner, version)

    monkeypatch.setattr(locks, "_lock_put", partition)
    with pytest.raises(LockLost):
        with guard(locks, lease_duration=0.3) as lease:
            eventually(lambda: lease.metrics.lost)
            assert lease.metrics.renewals == 0
            with pytest.raises(LockLost):
                lease.raise_if_lost()
    requests = lease.metrics.write_requests
    time.sleep(0.12)
    assert lease.metrics.write_requests == requests


def test_late_renewal_cannot_revive_expired_guard(locks, monkeypatch):
    # A delayed successful callback exercises the post-response deadline check.
    # Real HTTP deadline/cancellation behavior is tested separately.
    original = locks._lock_put

    def delayed(table, item, owner, version):
        if owner is not None:
            time.sleep(0.3)
        return original(table, item, owner, version)

    monkeypatch.setattr(locks, "_lock_put", delayed)
    with pytest.raises(LockLost):
        with guard(locks, lease_duration=0.3) as lease:
            eventually(lambda: lease.metrics.lost)
            assert lease.metrics.renewals == 0
    assert stored(locks) is None


def test_acquisition_response_after_wait_deadline_never_enters(locks, monkeypatch):
    original = locks._lock_put

    def late(*args):
        original(*args)
        time.sleep(0.06)

    monkeypatch.setattr(locks, "_lock_put", late)
    lease = guard(locks, lease_duration=1, wait_timeout=0.02)
    with pytest.raises(LockLost, match="deadline"):
        with lease:
            pytest.fail("An acquisition after its wait deadline entered the body")
    eventually(lambda: stored(locks) is None)
    assert lease.metrics.renewals == 0


def test_transaction_rejects_different_client(locks):
    with MemoryBackend() as other:
        with guard(locks) as lease:
            with pytest.raises(ValueError, match="same client"):
                lease.check_in(SyncTransaction(other.client))


@pytest.mark.parametrize("schema", [None, {"partition_key": ("pk", "S")}])
def test_memory_lock_requires_a_matching_table(schema):
    with MemoryBackend() as backend:
        if schema:
            backend.client.sync_create_table("locks", **schema)
        expected = ValidationException if schema else ResourceNotFoundException
        with pytest.raises(expected):
            with guard(backend.client):
                pytest.fail("A mismatched lock table entered the block")


def test_declared_keys_preserve_legacy_seed_inference():
    # Schema support for lock tables must preserve existing common-key seeds.
    with MemoryBackend(seed={"data": [{"id": "a"}, {"id": "b"}]}) as backend:
        assert backend.client.sync_get_item("data", {"id": "a"}) == {"id": "a"}
        assert backend.client.sync_get_item("data", {"id": "b"}) == {"id": "b"}


@settings(max_examples=15, deadline=None)
@given(
    st.lists(st.sampled_from(["acquire", "contend", "release", "replace"]), min_size=1, max_size=20)
)
def test_generated_ownership_sequences(operations):
    """Check ownership invariants across generated lifecycle sequences."""
    with MemoryBackend() as backend:
        client = backend.client
        client.sync_create_table("locks", partition_key=("key", "S"))
        current = None
        current_owner = None
        try:
            for operation in operations:
                if operation == "acquire" and current is None:
                    client.sync_delete_item("locks", {"key": "work"})
                    current = guard(client)
                    current.__enter__()
                    current_owner = stored(client)["owner"]
                elif operation == "contend" and current is not None:
                    with pytest.raises(LockNotAcquired):
                        with guard(client, wait_timeout=0):
                            pytest.fail("A second owner entered")
                elif operation == "replace" and current is not None:
                    successor = abandoned(client, owner=f"successor-{random.random()}")
                    with pytest.raises(LockLost):
                        current.__exit__(None, None, None)
                    assert stored(client) == successor
                    current = None
                elif operation == "release" and current is not None:
                    assert stored(client)["owner"] == current_owner
                    current.__exit__(None, None, None)
                    current = None
                    assert stored(client) is None
        finally:
            if current is not None:
                current.__exit__(None, None, None)
