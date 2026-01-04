# PartiQL

Execute SQL-like queries on DynamoDB using PartiQL syntax.

## What is PartiQL?

PartiQL is a SQL-compatible query language created by AWS. It lets you use familiar SQL syntax (`SELECT`, `INSERT`, `UPDATE`, `DELETE`) to work with DynamoDB instead of the native API expressions.

DynamoDB added PartiQL support in 2020. It's useful when:

- You're coming from a SQL background
- You want simpler ad-hoc queries
- You prefer SQL syntax over DynamoDB expressions

Under the hood, PartiQL queries are converted to native DynamoDB operations. Performance is the same as using the native API.

!!! note
    PartiQL is not a replacement for the native API. It's an alternative syntax. Both use the same underlying DynamoDB operations.

## Key features

- SQL-compatible syntax for DynamoDB
- Parameterized queries with `?` placeholders
- Works with both Client and Model
- Async support
- Metrics (duration, RCU, item count)

## Getting started

### Basic select

Use `execute_statement()` to run PartiQL queries:

=== "basic_select.py"
    ```python
    --8<-- "docs/examples/partiql/basic_select.py"
    ```

The result is a list you can iterate over. It also has `.metrics` and `.next_token` attributes.

### Select specific columns

Fetch only the columns you need:

=== "select_columns.py"
    ```python
    --8<-- "docs/examples/partiql/select_columns.py"
    ```

### With Model (typed results)

Use `Model.execute_statement()` to get typed model instances:

=== "model_execute.py"
    ```python
    --8<-- "docs/examples/partiql/model_execute.py"
    ```

This gives you full IDE autocomplete and type checking.

## Advanced

### Async

Use `async_execute_statement()` for async code:

=== "async_partiql.py"
    ```python
    --8<-- "docs/examples/partiql/async_partiql.py"
    ```

### Consistent reads

For strongly consistent reads:

```python
result = client.execute_statement(
    "SELECT * FROM users WHERE pk = ?",
    parameters=["USER#123"],
    consistent_read=True,
)
```

### Pagination

For large result sets, use `next_token`:

```python
result = client.execute_statement("SELECT * FROM users")

# Process first page
for item in result:
    print(item)

# Fetch next page if available
if result.next_token:
    next_page = client.execute_statement(
        "SELECT * FROM users",
        next_token=result.next_token,
    )
```

### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `statement` | str | Required | PartiQL statement |
| `parameters` | list | None | Values for `?` placeholders |
| `consistent_read` | bool | False | Strongly consistent read |
| `next_token` | str | None | Pagination token |

## PartiQL vs Query

When should you use PartiQL vs the native Query API?

| Feature | PartiQL | Query |
|---------|---------|-------|
| Syntax | SQL-like | DynamoDB expressions |
| Learning curve | Easier if you know SQL | DynamoDB-specific |
| Performance | Same | Same |
| Type safety | Manual | Attribute conditions |
| Auto pagination | Manual (next_token) | Automatic iterator |

Use PartiQL when:

- You prefer SQL syntax
- You're migrating from SQL databases
- You want simpler ad-hoc queries
- You're doing one-off data exploration

Use Query when:

- You want type-safe conditions with model attributes
- You need automatic pagination
- You're building complex filter logic
- You want IDE autocomplete for conditions

## Supported statements

PartiQL in DynamoDB supports:

| Statement | Example |
|-----------|---------|
| SELECT | `SELECT * FROM users WHERE pk = ?` |
| INSERT | `INSERT INTO users VALUE {'pk': 'USER#1', 'name': 'Alice'}` |
| UPDATE | `UPDATE users SET name = 'Bob' WHERE pk = 'USER#1'` |
| DELETE | `DELETE FROM users WHERE pk = 'USER#1'` |

!!! warning
    pydynox currently only supports `SELECT` via `execute_statement()`. For INSERT/UPDATE/DELETE, use the native `save()`, `update()`, and `delete()` methods which provide better type safety and hooks support.

## Next steps

- [Query](query.md) - Type-safe queries with model attributes
- [Conditions](conditions.md) - Build filter conditions
- [Async](async.md) - Async operations

