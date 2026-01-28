# Benchmarks

pydynox is built for speed. We run benchmarks on AWS Lambda to measure real-world performance against boto3 and PynamoDB.

!!! note "Live dashboard coming soon"
    We're setting up a public CloudWatch dashboard so you can see the results in real time. Link will be shared here once it's ready.

## Why Lambda?

Lambda is a good test environment because:

- Cold starts matter - every millisecond counts
- Memory is limited - efficiency is important
- Pay per millisecond - faster code = lower cost

The results apply to other environments too. If pydynox is fast on Lambda with 128MB, it will be fast anywhere.

## What we test

We compare three libraries doing the same operations:

| Library | Description |
|---------|-------------|
| pydynox | Rust core with Python bindings |
| boto3 | AWS SDK for Python (raw client) |
| PynamoDB | Popular Python ORM for DynamoDB |

Operations tested:

- **Basic**: put_item, get_item, update_item, delete_item, query
- **Batch**: batch_write, batch_get
- **Advanced**: encryption (KMS), compression (zstd), S3 large objects

## Results

### Basic operations (128MB ARM64)

At low memory, pydynox shines. The Rust core does heavy lifting without consuming Python memory.

| Operation | pydynox | boto3 | PynamoDB |
|-----------|---------|-------|----------|
| put_item p50 | ~10ms | ~30ms | ~40ms |
| get_item p50 | ~3ms | ~12ms | ~25ms |

pydynox is 3-4x faster than boto3 and 4-8x faster than PynamoDB for basic operations.

### Basic operations (2048MB ARM64)

With more memory, Python has room to breathe. The latency gap narrows, but pydynox still wins.

| Operation | pydynox | boto3 | PynamoDB |
|-----------|---------|-------|----------|
| put_item p50 | ~4ms | ~5ms | ~6ms |
| get_item p50 | ~2ms | ~3ms | ~11ms |

The tradeoff: more memory costs more money. pydynox gives you the same speed at lower memory. We're adding memory usage metrics to the dashboard so you can see exactly how much each library consumes.

### Advanced operations (encryption and compression)

This is where pydynox really stands out. Encryption and compression run in Rust, not Python.

| Operation | pydynox | boto3 + KMS | PynamoDB + KMS |
|-----------|---------|-------------|----------------|
| put_encrypted p50 | ~17ms | ~60ms | ~64ms |
| get_encrypted p50 | ~16ms | ~40ms | ~64ms |
| put_compressed p50 | ~14ms | ~27ms | ~40ms |
| get_compressed p50 | ~12ms | ~26ms | ~40ms |

pydynox is 3-4x faster for encryption and 2x faster for compression.

## Why pydynox is faster

### The Python problem

Python is great for writing code fast. But it's not great for running code fast.

Every DynamoDB operation involves work that Python does slowly:

- **Serialization** - Converting your objects to DynamoDB format
- **Deserialization** - Converting DynamoDB responses back to objects
- **Type conversion** - Turning Python types into DynamoDB types (and back)
- **String building** - Creating condition expressions, update expressions
- **Validation** - Checking types, sizes, constraints

In pure Python libraries, all this happens in the interpreter. The GIL (Global Interpreter Lock) means only one thread runs Python code at a time. More work = more time holding the GIL = slower.

### Moving work to Rust

pydynox takes a different approach. Python handles what Python is good at:

- Nice API for developers
- Type hints for IDE support
- Easy configuration

Rust handles what Rust is good at:

- Fast serialization/deserialization
- Efficient string operations
- CPU-heavy work (compression, encryption)
- Memory-efficient batch processing

The result: Python code stays simple, but the heavy lifting happens at native speed.

### Why this matters

When you call `user.save()` in pydynox:

1. Python collects your data (fast - just attribute access)
2. Rust serializes it to DynamoDB format (fast - native code)
3. Rust builds the request (fast - native code)
4. AWS SDK sends it (network time - same for everyone)
5. Rust deserializes the response (fast - native code)
6. Python returns the result (fast - just returning)

Steps 2, 3, and 5 are where pure Python libraries spend most of their CPU time. pydynox does them in Rust.

### Memory efficiency

At 128MB Lambda, Python has ~50MB for your code after the runtime loads.

pydynox's Rust core uses its own memory space. This leaves more room for Python to work with. Less memory pressure = fewer garbage collections = faster execution.

## Known limitations

### update_item and delete_item

Current benchmarks show pydynox slower for update/delete. This is because the test does:

```python
item = Model.get(pk="...")  # GET first
item.update(data="new")     # then UPDATE
```

We're adding `update_by_key()` and `delete_by_key()` methods to do direct updates without fetching first. See [issue #92](https://github.com/ferrumio/pydynox/issues/92).

### query

Query is slower because pydynox creates Model instances for each result. boto3 returns raw dicts.

We're adding `query_raw()` for cases where you need speed over convenience.

## Running your own benchmarks

The benchmark infrastructure is in `benchmarks/` folder. It uses CDK to deploy:

- 30 Lambda functions (10 per library × 3 libraries)
- 5 memory sizes: 128MB, 256MB, 512MB, 1024MB, 2048MB
- 2 architectures: ARM64, x86_64
- CloudWatch Dashboard with all metrics

To deploy:

```bash
cd benchmarks
pip install -r requirements.txt
cdk deploy
```

## Future improvements

We plan to add:

- Memory usage metrics (not just latency)
- Cold start comparison
- Concurrent request handling
- Larger payload sizes

We want pydynox to be fast and efficient. These benchmarks help us find where to improve.
