# Lock workloads

Run from the repository with the native extension installed:

```bash
uv run python benchmarks/locks/run.py --localstack --hold 600 > /tmp/locks.json
```

The JSON report goes to stdout; progress goes to stderr. Use shell redirection
to save the report.

The runner creates and removes its own table. It measures uncontended calls,
contenders sharing one key, independent keys, simultaneous renewing locks,
abandoned-owner recovery, and an optional ten-minute hold.

Each result includes acquisition and cycle p50/p95/p99, per-worker completions,
failures, request counts, reported capacity, process CPU, and peak RSS. RSS is the
process high-water mark, not an isolated allocation count for each workload.
Capacity on failed or lost responses is not included in returned capacity totals.

For AWS measurements, pass an explicit `--endpoint` and `--region`, using the
normal credential chain. This creates billable resources and requests. Build with
`uv run maturin develop --release` for performance comparisons and record the
build profile, host, Region, and concurrency alongside results.

LocalStack validates workloads and request counts. Its latency and capacity
reports are not production AWS benchmarks. A successful finite contention run
does not establish FIFO fairness or freedom from starvation.

The process pause/kill experiments and an independent transaction check live in
`tests/integration/test_distributed_lock.py`. Network fault tests forward actual
SDK requests to LocalStack while delaying responses or blocking renewal.

## Local validation: September 30, 2026

The [recorded run](results/localstack-2026-09-30.json) used a development build,
Python 3.14.7, and LocalStack 4.4.0 on Linux aarch64. Other tests ran on the same
host, so use these results to inspect behavior and counts, not to compare speed.

| Workload | Completed guards | Writes | Reads | Renewals | Conditional failures |
|----------|------------------|--------|-------|----------|----------------------|
| Short, uncontended calls | 100 | 200 | 0 | 0 | 0 |
| Ten contenders, one key | 50 | 114 | 42 | 0 | 14 |
| Ten independent keys | 50 | 100 | 0 | 0 | 0 |
| Ten active locks, four seconds | 10 | 50 | 0 | 30 | 0 |
| Abandoned owner, three-second lease | 1 | 3 | 7 | 0 | 1 |
| Ten-minute hold, 30-second lease | 1 | 61 | 0 | 59 | 0 |

No guard failed in this run. All contenders completed their five calls; this
finite run does not prove fairness. The ten-minute hold confirms
`1 acquisition + 59 renewals + 1 release = 61 writes`.

AWS measurements and a comparison with another implementation remain open in
RFC #499. LocalStack tests also passed process kill/pause, stale transaction
rejection, lost responses, cancellation, and renewal partitions.
