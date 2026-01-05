# ADR 011: Prepare/Execute Pattern for Rust Operations

## Status

Accepted

## Context

We need to support both sync and async operations in Rust. The AWS SDK is async-only, so we need a way to:

1. Share code between sync and async paths to avoid duplication
2. Convert Python types to Rust types once (not twice)
3. Keep the code DRY and maintainable

## Decision

Use a three-phase pattern for all DynamoDB operations:

1. **Prepare**: Convert Python types to Rust types
2. **Execute**: Run the async AWS SDK call
3. **Convert**: Transform results back to Python

```
┌─────────────────────────────────────────────────────────────┐
│                    Python calls Rust                        │
│                                                             │
│   Sync:  client.scan(table, filter=...)                    │
│   Async: client.async_scan(table, filter=...)              │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│              Phase 1: PREPARE (shared)                      │
│                                                             │
│   prepare_scan(py, table, filter, ...) -> PreparedScan     │
│                                                             │
│   - Convert PyDict to HashMap<String, AttributeValue>       │
│   - Extract expression names/values                         │
│   - Validate parameters                                     │
│   - Return a Rust struct with all data ready                │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│              Phase 2: EXECUTE (shared)                      │
│                                                             │
│   async fn execute_scan(client, prepared) -> RawResult     │
│                                                             │
│   - Build AWS SDK request                                   │
│   - Call AWS SDK (async)                                    │
│   - Measure duration                                        │
│   - Return raw Rust types (no Python)                       │
└─────────────────────────────────────────────────────────────┘
                            │
              ┌─────────────┴─────────────┐
              │                           │
              ▼                           ▼
┌─────────────────────────┐   ┌─────────────────────────┐
│   Sync: scan()          │   │   Async: async_scan()   │
│                         │   │                         │
│   runtime.block_on(     │   │   future_into_py(       │
│     execute_scan(...)   │   │     execute_scan(...)   │
│   )                     │   │   )                     │
│                         │   │                         │
│   Convert to Python     │   │   Convert to Python     │
│   Return immediately    │   │   Return awaitable      │
└─────────────────────────┘   └─────────────────────────┘
```

## Example: Scan Operation

```rust
// Phase 1: Prepare - shared between sync and async
pub struct PreparedScan {
    pub table: String,
    pub filter_expression: Option<String>,
    pub expression_attribute_names: Option<HashMap<String, String>>,
    pub expression_attribute_values: Option<HashMap<String, AttributeValue>>,
    pub limit: Option<i32>,
    // ... other fields
}

pub fn prepare_scan(
    py: Python<'_>,
    table: &str,
    filter_expression: Option<String>,
    expression_attribute_names: Option<&Bound<'_, PyDict>>,
    // ... other params
) -> PyResult<PreparedScan> {
    // Convert Python types to Rust types ONCE
    let names = convert_names(expression_attribute_names)?;
    let values = convert_values(py, expression_attribute_values)?;
    
    Ok(PreparedScan {
        table: table.to_string(),
        filter_expression,
        expression_attribute_names: names,
        expression_attribute_values: values,
        // ...
    })
}

// Phase 2: Execute - shared async core
pub async fn execute_scan(
    client: Client,
    prepared: PreparedScan,
) -> Result<RawScanResult, SdkError> {
    let mut request = client.scan().table_name(&prepared.table);
    
    if let Some(filter) = prepared.filter_expression {
        request = request.filter_expression(filter);
    }
    // ... build request
    
    let start = Instant::now();
    let result = request.send().await?;
    let duration = start.elapsed();
    
    // Return raw Rust types (no Python conversion yet)
    Ok(RawScanResult {
        items: result.items.unwrap_or_default(),
        last_evaluated_key: result.last_evaluated_key,
        duration_ms: duration.as_secs_f64() * 1000.0,
    })
}

// Sync wrapper
pub fn scan(py: Python<'_>, client: &Client, runtime: &Runtime, ...) -> PyResult<ScanResult> {
    let prepared = prepare_scan(py, ...)?;  // Phase 1
    
    let raw = runtime.block_on(execute_scan(client.clone(), prepared))?;  // Phase 2
    
    raw_to_py_result(py, raw)  // Phase 3: Convert to Python
}

// Async wrapper
pub fn async_scan<'py>(py: Python<'py>, client: Client, ...) -> PyResult<Bound<'py, PyAny>> {
    let prepared = prepare_scan(py, ...)?;  // Phase 1
    
    pyo3_async_runtimes::tokio::future_into_py(py, async move {
        let raw = execute_scan(client, prepared).await?;  // Phase 2
        
        Python::with_gil(|py| raw_to_py_result(py, raw))  // Phase 3
    })
}
```

## Why This Pattern?

### 1. No duplicate Python conversion

Without this pattern, you'd convert Python types twice:

```rust
// BAD: Converting in both sync and async
pub fn scan(...) {
    let names = convert_names(py_names)?;  // Convert here
    // ...
}

pub fn async_scan(...) {
    let names = convert_names(py_names)?;  // Convert again here
    // ...
}
```

With prepare/execute:

```rust
// GOOD: Convert once in prepare
let prepared = prepare_scan(py, ...)?;  // Convert once
// Both sync and async use prepared
```

### 2. Clean separation of concerns

- `prepare_*`: Handles Python ↔ Rust type conversion
- `execute_*`: Pure async Rust, no Python types
- Wrappers: Handle sync/async differences

### 3. Easier testing

The `execute_*` function is pure Rust with no Python dependencies. It can be tested with standard Rust tests if needed.

### 4. GIL management

The `execute_*` function doesn't hold the GIL. For async operations, we only acquire the GIL at the end to convert results.

## Naming Convention

| Phase | Function Name | Returns |
|-------|---------------|---------|
| Prepare | `prepare_scan`, `prepare_query`, etc. | `PreparedScan`, `PreparedQuery` |
| Execute | `execute_scan`, `execute_query`, etc. | `RawScanResult`, `RawQueryResult` |
| Sync wrapper | `scan`, `query`, etc. | `PyResult<ScanResult>` |
| Async wrapper | `async_scan`, `async_query`, etc. | `PyResult<Bound<'py, PyAny>>` |

## Consequences

### Positive

- Code reuse between sync and async
- Single point for Python type conversion
- Clear separation of concerns
- Easier to maintain and extend

### Negative

- More structs (`PreparedX`, `RawXResult`)
- Slightly more boilerplate
- Need to understand the pattern to contribute
