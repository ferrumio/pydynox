# Item size calculator

Check item sizes before saving to avoid DynamoDB's 400KB limit.

## Key features

- Calculate item size in bytes, KB, and percent of limit
- Get per-field breakdown to find large fields
- Auto-check on save with `max_size` config
- Raises `ItemTooLargeError` before hitting DynamoDB

## Getting started

### Basic usage

Call `calculate_size()` on any model instance:

=== "basic_size.py"
    ```python
    --8<-- "docs/examples/size/basic_size.py"
    ```

Output:

```
Size: 52 bytes
Size: 0.05 KB
Percent of limit: 0.0%
Over limit: False
```

The `ItemSize` object has these properties:

| Property | Type | Description |
|----------|------|-------------|
| `bytes` | int | Total size in bytes |
| `kb` | float | Total size in kilobytes |
| `percent` | float | Percentage of 400KB limit used |
| `is_over_limit` | bool | True if item exceeds 400KB |
| `fields` | dict | Per-field breakdown (only with `detailed=True`) |

### Detailed breakdown

Pass `detailed=True` to see which fields use the most space:

=== "detailed_breakdown.py"
    ```python
    --8<-- "docs/examples/size/detailed_breakdown.py"
    ```

Output:

```
Total: 10089 bytes

Per field:
  body: 10003 bytes
  metadata: 42 bytes
  tags: 24 bytes
  title: 15 bytes
  pk: 5 bytes
```

This helps you find which fields to optimize when items get too big.

### Auto-check on save

Set `max_size` in your model's Meta to check size before saving:

=== "max_size_limit.py"
    ```python
    --8<-- "docs/examples/size/max_size_limit.py"
    ```

Output:

```
Item too large: 20024 bytes
Max allowed: 10000 bytes
Item key: {'pk': 'POST#1', 'sk': 'COMMENT#1'}
```

The check happens before calling DynamoDB. This saves you a round trip and gives a clearer error message.

## How DynamoDB calculates size

DynamoDB counts bytes differently for each type:

| Type | Size calculation |
|------|------------------|
| String | UTF-8 byte length |
| Number | 1 byte + 1 byte per 2 significant digits |
| Binary | Byte length |
| Boolean | 1 byte |
| Null | 1 byte |
| List | 3 bytes + size of each element |
| Map | 3 bytes + size of each key + size of each value |
| Set | 3 bytes + size of each element |

Attribute names also count. A field named `description` adds 11 bytes just for the name.

!!! tip
    Use short attribute names in high-volume tables. `d` instead of `description` saves 10 bytes per item.

## Error handling

Catch `ItemTooLargeError` to handle oversized items:

```python
from pydynox.exceptions import ItemTooLargeError

try:
    user.save()
except ItemTooLargeError as e:
    print(f"Item is {e.size} bytes, max is {e.max_size}")
    # Maybe compress the data or split into multiple items
```

The error includes:

| Attribute | Type | Description |
|-----------|------|-------------|
| `size` | int | Actual item size in bytes |
| `max_size` | int | Configured limit in bytes |
| `item_key` | dict | The item's key (pk, sk) |

## When to use this

- **Before saving large items** - Check size to avoid errors
- **Debugging size issues** - Find which fields are too big
- **Setting limits** - Enforce smaller limits than 400KB for your app
- **Monitoring** - Track item sizes over time
