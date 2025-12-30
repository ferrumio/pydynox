# Getting started

This guide walks you through installing pydynox and creating your first model. By the end, you'll have a working DynamoDB model with CRUD operations.

## Key features

- Install with pip or uv
- Define models with typed attributes
- CRUD operations with simple methods
- Local development with DynamoDB Local

## Installation

=== "pip"
    ```bash
    pip install pydynox
    ```

=== "uv"
    ```bash
    uv add pydynox
    ```

To verify the installation:

```python
import pydynox
print(pydynox.__version__)
```

## Your first model

Let's create a simple User model. A model is a Python class that represents items in a DynamoDB table.

=== "basic_model.py"
    ```python
    --8<-- "docs/examples/models/basic_model.py"
    ```

Here's what each part does:

- `class Meta` - Configuration for the model. `table` is the DynamoDB table name.
- `pk = StringAttribute(hash_key=True)` - The partition key. Every item needs one.
- `sk = StringAttribute(range_key=True)` - The sort key. Optional, but useful for complex access patterns.
- Other attributes - Regular fields with their types and optional defaults.

## Basic operations

Now let's use the model to work with DynamoDB:

=== "crud_operations.py"
    ```python
    --8<-- "docs/examples/models/crud_operations.py"
    ```

### Create

Instantiate your model and call `save()`:

```python
user = User(pk="USER#123", sk="PROFILE", name="John", age=30)
user.save()
```

### Read

Use `get()` with the key attributes:

```python
user = User.get(pk="USER#123", sk="PROFILE")
if user:
    print(user.name)
```

### Update

Change attributes and save, or use `update()` for partial updates:

```python
# Full update
user.name = "Jane"
user.save()

# Partial update
user.update(name="Jane", age=31)
```

### Delete

Call `delete()` on an instance:

```python
user.delete()
```

## Configuration

The `Meta` class configures how your model connects to DynamoDB:

```python
class User(Model):
    class Meta:
        table = "users"           # Required - table name
        region = "us-east-1"      # Optional - AWS region
        endpoint_url = None       # Optional - for local testing
```

## Local development

For local testing, use [DynamoDB Local](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/DynamoDBLocal.html). It's a downloadable version of DynamoDB that runs on your machine.

Start DynamoDB Local (using Docker):

```bash
docker run -p 8000:8000 amazon/dynamodb-local
```

Then point your model to it:

```python
class User(Model):
    class Meta:
        table = "users"
        endpoint_url = "http://localhost:8000"
```

!!! tip
    DynamoDB Local is great for development and testing. You don't need AWS credentials, and you won't accidentally modify production data.

## Next steps

Now that you have the basics working:

- [Models](guides/models.md) - Learn about all attribute types and options
- [Batch operations](guides/batch.md) - Work with multiple items efficiently
- [Rate limiting](guides/rate-limiting.md) - Control throughput to avoid throttling
- [Lifecycle hooks](guides/hooks.md) - Add validation and logging
