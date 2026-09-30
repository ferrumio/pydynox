"""Reproducible lock workloads; use --localstack for a local run."""

import argparse
import asyncio
import json
import platform
import resource
import statistics
import time
from contextlib import nullcontext
from pathlib import Path
from uuid import uuid4

from pydynox import DynamoDBClient
from pydynox.lock import DistributedLock


def percentiles(values):
    ordered = sorted(values)
    return (
        {
            label: round(ordered[min(len(ordered) - 1, int((len(ordered) - 1) * quantile))], 3)
            for label, quantile in (("p50", 0.50), ("p95", 0.95), ("p99", 0.99))
        }
        if values
        else {}
    )


async def workload(client, table, name, concurrency, samples, lease_duration, hold, shared):
    acquisitions, cycles, snapshots, failures = [], [], [], []
    completions = [0] * concurrency
    usage = resource.getrusage(resource.RUSAGE_SELF)
    cpu_start = usage.ru_utime + usage.ru_stime
    started = time.perf_counter()

    async def worker(index):
        for iteration in range(samples):
            key = f"{name}:shared" if shared else f"{name}:{index}:{iteration}"
            lease = DistributedLock(
                client,
                table=table,
                key=key,
                lease_duration=lease_duration,
                wait_timeout=35,
            )
            before = time.perf_counter()
            try:
                async with lease:
                    acquisitions.append((time.perf_counter() - before) * 1000)
                    await asyncio.sleep(hold)
                    lease.raise_if_lost()
                completions[index] += 1
                cycles.append((time.perf_counter() - before) * 1000)
            except Exception as error:
                failures.append(type(error).__name__)
            snapshots.append(lease.metrics)

    await asyncio.gather(*(worker(index) for index in range(concurrency)))
    usage = resource.getrusage(resource.RUSAGE_SELF)
    metrics = {
        field: sum(getattr(snapshot, field) for snapshot in snapshots)
        for field in (
            "read_requests",
            "write_requests",
            "conditional_failures",
            "request_failures",
            "renewals",
            "consumed_rcu",
            "consumed_wcu",
        )
    }
    result = {
        "workload": name,
        "concurrency": concurrency,
        "samples_per_worker": samples,
        "lease_seconds": lease_duration,
        "hold_seconds": hold,
        "elapsed_seconds": round(time.perf_counter() - started, 3),
        "acquisition_ms": percentiles(acquisitions),
        "cycle_ms": percentiles(cycles),
        "mean_cycle_ms": round(statistics.mean(cycles), 3) if cycles else None,
        "failures": failures,
        "completions_per_worker": completions,
        "cpu_seconds": round(usage.ru_utime + usage.ru_stime - cpu_start, 3),
        "process_peak_rss_kib": usage.ru_maxrss,
        **metrics,
    }
    print(json.dumps(result), flush=True)
    return result


async def run(args, endpoint):
    client = DynamoDBClient(
        endpoint_url=endpoint,
        region=args.region,
        **({"access_key": "testing", "secret_key": "testing"} if args.localstack else {}),
    )
    table = f"pydynox-lock-benchmark-{uuid4().hex}"
    await client.create_table(table, partition_key=("key", "S"), wait=True)
    results = []
    try:
        for name, concurrency, samples, lease, hold, shared in [
            ("uncontended", 1, args.samples, 30, 0, False),
            ("one_key", args.concurrency, 5, 3, 0.01, True),
            ("independent_keys", args.concurrency, 5, 3, 0.01, False),
            ("active_locks", args.concurrency, 1, 3, 4, False),
        ]:
            results.append(
                await workload(
                    client,
                    table,
                    name,
                    concurrency,
                    samples,
                    lease,
                    hold,
                    shared,
                )
            )
        await client.put_item(
            table,
            {
                "key": "recovery:shared",
                "owner": "dead",
                "version": "old",
                "lease_ms": 3000,
                "protocol": 1,
            },
        )
        results.append(await workload(client, table, "recovery", 1, 1, 3, 0, True))
        if args.hold:
            results.append(await workload(client, table, "long_hold", 1, 1, 30, args.hold, False))
    finally:
        await client.delete_table(table)
    report = {
        "environment": "LocalStack 4.4.0" if args.localstack else "AWS/custom endpoint",
        "region": args.region,
        "platform": platform.platform(),
        "python": platform.python_version(),
        "table": "dedicated key(S), no indexes or TTL",
        "capacity_note": "Successful responses only; failures may consume additional units.",
        "item_note": "UUID owner/version; key length varies by workload; each row is under 1 KiB.",
        "workloads": results,
    }
    if args.output:
        args.output.write_text(json.dumps(report, indent=2) + "\n")
    return int(any(result["failures"] for result in results))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    destination = parser.add_mutually_exclusive_group(required=True)
    destination.add_argument("--localstack", action="store_true")
    destination.add_argument("--endpoint", help="Explicit DynamoDB endpoint; may incur AWS costs")
    parser.add_argument("--region", default="us-east-1")
    parser.add_argument("--samples", type=int, default=100)
    parser.add_argument("--concurrency", type=int, default=10)
    parser.add_argument("--hold", type=float, default=0, help="Long-hold duration in seconds")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.samples < 1 or args.concurrency < 1 or args.hold < 0:
        parser.error("samples/concurrency must be positive and hold must be nonnegative")
    if args.localstack:
        from testcontainers.localstack import LocalStackContainer

        environment = LocalStackContainer("localstack/localstack:4.4.0").with_services("dynamodb")
    else:
        environment = nullcontext()
    with environment as container:
        endpoint = container.get_url() if container else args.endpoint
        raise SystemExit(asyncio.run(run(args, endpoint)))


if __name__ == "__main__":
    main()
