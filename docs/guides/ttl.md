# TTL (Time-To-Live)

Auto-delete items after a set time using DynamoDB's TTL feature.

## What is TTL?

DynamoDB TTL lets you set an expiration time on items. When the time passes, DynamoDB automatically deletes the item. This is useful for:

- Session tokens
- Temporary data
- Cache entries
- Trial periods
- Audit logs with retention

TTL deletion is free - you don't pay for the delete operation. Items are usually deleted within 48 hours of expiration (often much faster).

!!! note
    TTL must be enabled on your table. See [AWS docs](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/TTL.html) for setup.

## Key features

- `TTLAttribute` - stores datetime as epoch timestamp
- `ExpiresIn` helper - easy time calculations
- `is_expired` property - check if item expired
- `expires_in` property - get time remaining
- `extend_ttl()` method - extend expiration

## Getting started

### Basic usage

Add a `TTLAttribute` to your model:

=== "basic_ttl.py"
    ```python
    --8<-- "docs/examples/ttl/basic_ttl.py"
    ```

### ExpiresIn helper

Use `ExpiresIn` to calculate expiration times:

=== "expires_in_helper.py"
    ```python
    --8<-- "docs/examples/ttl/expires_in_helper.py"
    ```

| Method | Example | Description |
|--------|---------|-------------|
| `ExpiresIn.seconds(n)` | `ExpiresIn.seconds(30)` | n seconds from now |
| `ExpiresIn.minutes(n)` | `ExpiresIn.minutes(15)` | n minutes from now |
| `ExpiresIn.hours(n)` | `ExpiresIn.hours(1)` | n hours from now |
| `ExpiresIn.days(n)` | `ExpiresIn.days(7)` | n days from now |
| `ExpiresIn.weeks(n)` | `ExpiresIn.weeks(2)` | n weeks from now |

All methods return a `datetime` in UTC.

## Checking expiration

### is_expired

Check if an item has expired:

=== "check_expiration.py"
    ```python
    --8<-- "docs/examples/ttl/check_expiration.py"
    ```

`is_expired` returns:

- `True` if the TTL time has passed
- `False` if not expired or no TTL attribute

### expires_in

Get time remaining until expiration:

```python
remaining = session.expires_in

if remaining:
    print(f"Expires in {remaining.total_seconds()} seconds")
    print(f"Expires in {remaining.total_seconds() / 60} minutes")
else:
    print("Already expired or no TTL")
```

`expires_in` returns:

- `timedelta` if not expired
- `None` if expired or no TTL attribute

## Extending TTL

Use `extend_ttl()` to push back the expiration:

=== "extend_ttl.py"
    ```python
    --8<-- "docs/examples/ttl/extend_ttl.py"
    ```

This updates both the local instance and DynamoDB in one call.

## Real-world example

Session management with TTL:

=== "session_example.py"
    ```python
    --8<-- "docs/examples/ttl/session_example.py"
    ```

## How it works

1. `TTLAttribute` stores datetime as Unix epoch timestamp (number)
2. DynamoDB's TTL process scans for expired items
3. Expired items are deleted automatically (usually within 48 hours)
4. No cost for TTL deletions

!!! warning
    Items may remain readable for up to 48 hours after expiration. Always check `is_expired` in your code if you need strict expiration.

## Best practices

1. **Always check is_expired** - Don't rely only on DynamoDB deletion
2. **Use UTC** - `ExpiresIn` returns UTC times, keep everything in UTC
3. **Enable TTL on table** - TTL won't work without table-level configuration
4. **Choose the right duration** - Too short = bad UX, too long = wasted storage

## Next steps

- [Attributes](attributes.md) - All attribute types
- [Models](models.md) - Model basics
- [Hooks](hooks.md) - Run code before/after operations
