# Model inheritance

Share attributes across models and let pydynox figure out which class to use when loading items.

## Key features

- Base classes with shared attributes (timestamps, audit fields, etc.)
- Discriminator field for single-table design
- Automatic type resolution on get/query/scan
- Deep inheritance (Dog → Animal → Model)
- Zero overhead - just Python classes

## Why use inheritance?

### Problem 1: Repeated attributes

Every model needs `created_at`, `updated_at`, `created_by`. Copy-paste is error-prone:

```python
# Without inheritance - copy-paste everywhere
class User(Model):
    pk = StringAttribute(partition_key=True)
    name = StringAttribute()
    created_at = DatetimeAttribute()  # repeated
    updated_at = DatetimeAttribute()  # repeated

class Product(Model):
    pk = StringAttribute(partition_key=True)
    title = StringAttribute()
    created_at = DatetimeAttribute()  # repeated again
    updated_at = DatetimeAttribute()  # repeated again
```

### Problem 2: Single-table design

You store Dogs and Cats in the same table. When you load an item, you need to know which class to use:

```python
# Without discriminator - manual type checking
item = await client.get_item("animals", {"pk": "ANIMAL#1"})
if item["type"] == "dog":
    dog = Dog(**item)
elif item["type"] == "cat":
    cat = Cat(**item)
```

pydynox solves both problems with Python inheritance.

## Base classes

Create a base class with common attributes. Any model that inherits from it gets those attributes automatically:

=== "base_class.py"
    ```python
    --8<-- "docs/examples/inheritance/base_class.py"
    ```

The base class is just a regular Python class. No need to inherit from `Model`.

### Common base classes

| Base class | Attributes | Use case |
|------------|------------|----------|
| `TimestampBase` | `created_at`, `updated_at` | Track when items were created/modified |
| `AuditBase` | `created_by`, `updated_by` | Track who created/modified items |
| `SoftDeleteBase` | `deleted_at`, `is_deleted` | Soft delete pattern |
| `VersionBase` | `version` | Optimistic locking |

You can combine multiple base classes:

```python
class User(Model, TimestampBase, AuditBase):
    model_config = ModelConfig(table="users")
    pk = StringAttribute(partition_key=True)
    name = StringAttribute()
```

## Discriminator for single-table design

When you store different item types in the same table, add a discriminator field. pydynox uses it to return the correct class.

=== "discriminator.py"
    ```python
    --8<-- "docs/examples/inheritance/discriminator.py"
    ```

### How it works

1. Add `discriminator=True` to a `StringAttribute` in the parent model
2. Create subclasses that inherit from the parent
3. When you save, pydynox sets the discriminator to the class name (`"Dog"`, `"Cat"`)
4. When you load, pydynox reads the discriminator and returns the correct subclass

### Custom discriminator field

The discriminator field can have any name:

| Field name | Use case |
|------------|----------|
| `_type` | Internal field, hidden from API responses |
| `item_type` | Explicit, readable in DynamoDB console |
| `entity_type` | Common in single-table designs |
| `sk` | Part of sort key pattern (advanced) |

=== "custom_discriminator.py"
    ```python
    --8<-- "docs/examples/inheritance/custom_discriminator.py"
    ```

## Deep inheritance

Inheritance works at any depth. A `GoldenRetriever` can extend `Dog` which extends `Animal`:

=== "deep_inheritance.py"
    ```python
    --8<-- "docs/examples/inheritance/deep_inheritance.py"
    ```

When you call `Animal.get()`, pydynox returns the most specific class (`GoldenRetriever`, not `Dog` or `Animal`).

## Query and scan

When you query or scan from the parent class, pydynox returns the correct subclass for each item:

=== "query_scan.py"
    ```python
    --8<-- "docs/examples/inheritance/query_scan.py"
    ```

This is powerful for single-table design. One scan returns a mix of Dogs and Cats, each with the correct type.

## Combining base classes and discriminator

You can use both features together. This is common in real applications:

=== "combined.py"
    ```python
    --8<-- "docs/examples/inheritance/combined.py"
    ```

## Single-table design example

Here's a complete example of single-table design with inheritance:

```python
from pydynox import Model, ModelConfig
from pydynox.attributes import StringAttribute, NumberAttribute, BooleanAttribute


# Base class for audit fields
class AuditBase:
    created_by = StringAttribute()


# Parent model - all entities in one table
class Entity(Model, AuditBase):
    model_config = ModelConfig(table="app")
    pk = StringAttribute(partition_key=True)
    sk = StringAttribute(sort_key=True)
    entity_type = StringAttribute(discriminator=True)


# User entity
class User(Entity):
    model_config = ModelConfig(table="app")
    name = StringAttribute()
    email = StringAttribute()


# Order entity
class Order(Entity):
    model_config = ModelConfig(table="app")
    total = NumberAttribute()
    status = StringAttribute()


# Product entity
class Product(Entity):
    model_config = ModelConfig(table="app")
    title = StringAttribute()
    price = NumberAttribute()
    in_stock = BooleanAttribute()


async def main():
    # Save different entities to the same table
    await User(pk="USER#1", sk="PROFILE", name="John", email="john@example.com", created_by="system").save()
    await Order(pk="USER#1", sk="ORDER#001", total=99.99, status="pending", created_by="john").save()
    await Product(pk="PRODUCT#1", sk="DETAILS", title="Widget", price=9.99, in_stock=True, created_by="admin").save()

    # Query returns correct types
    user = await Entity.get(pk="USER#1", sk="PROFILE")
    assert isinstance(user, User)
    assert user.email == "john@example.com"

    order = await Entity.get(pk="USER#1", sk="ORDER#001")
    assert isinstance(order, Order)
    assert order.total == 99.99
```

## Performance

Inheritance has zero runtime overhead:

- Attribute collection happens once at class definition (import time)
- Discriminator lookup is a dict lookup (O(1))
- No reflection or introspection at runtime

The only cost is a few extra bytes for the discriminator field in DynamoDB.
