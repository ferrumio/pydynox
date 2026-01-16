# ADR 017: Direct AttributeValue to Python Conversion

## Status

Accepted

## Context

Query and scan operations were slower than expected compared to boto3 and PynamoDB. Benchmarks showed pydynox query at ~145ms p50 vs ~28ms for boto3/PynamoDB - a 5x difference.

Investigation revealed the conversion from DynamoDB `AttributeValue` to Python was doing two passes:

### Before (Double Conversion)

```
DynamoDB Response
      ↓
AttributeValue::S("hello")
      ↓
Python dict {"S": "hello"}    ← First conversion (Rust → Python dict)
      ↓
Python string "hello"         ← Second conversion (Python dict → native)
```

The code path was:

```rust
// Step 1: Create Python dict with DynamoDB format
fn attribute_value_to_py(py, value) {
    let dict = PyDict::new(py);
    match value {
        AttributeValue::S(s) => dict.set_item("S", s),
        // ...
    }
    dynamo_to_py(py, &dict)  // Step 2: Convert dict to native Python
}
```

This created unnecessary Python objects and called back into Python for the second conversion.

## Decision

Convert directly from Rust `AttributeValue` to native Python values in a single step.

### After (Direct Conversion)

```
DynamoDB Response
      ↓
AttributeValue::S("hello")
      ↓
Python string "hello"         ← Single conversion (Rust → native Python)
```

New code:

```rust
fn attribute_value_to_py_direct(py, value) {
    match value {
        AttributeValue::S(s) => Ok(s.into_pyobject(py)?),
        AttributeValue::N(n) => {
            // Parse and return int or float directly
            if n.contains('.') {
                Ok(n.parse::<f64>()?.into_pyobject(py)?)
            } else {
                Ok(n.parse::<i64>()?.into_pyobject(py)?)
            }
        }
        AttributeValue::Bool(b) => Ok(b.into_pyobject(py)?),
        AttributeValue::Null(_) => Ok(py.None()),
        // ... etc
    }
}
```

## Why Double Conversion Existed

The original design used DynamoDB's wire format (`{"S": "value"}`) as an intermediate representation. This made sense for:

1. Debugging - easy to see the DynamoDB types
2. Consistency - same format everywhere
3. Simplicity - one conversion function for both directions

But it added overhead for the hot path (query/scan results).

## Why Direct Conversion is Better

1. **Less work** - One conversion instead of two
2. **Less memory** - No intermediate Python dict per value
3. **Less GIL contention** - Fewer Python object allocations
4. **Faster** - Direct Rust → Python without Python callback

For a query returning 100 items with 10 attributes each:
- Before: 2000 Python object creations (1000 intermediate dicts + 1000 native values)
- After: 1000 Python object creations (just native values)

## Consequences

### Positive

- Query/scan deserialization is faster
- Less memory pressure during large result sets
- Simpler code path for the common case

### Negative

- Two conversion functions to maintain (direct and DynamoDB-format)
- Slightly more code in conversions.rs

### Neutral

- No API changes - users see the same Python values
- Binary data now returns `bytes` directly instead of base64 string

## Notes

This is one optimization. Other factors may also affect query performance:
- AWS SDK Rust HTTP client configuration
- Connection pooling settings
- Network latency

The full performance impact will be measured after deploying updated benchmarks.
