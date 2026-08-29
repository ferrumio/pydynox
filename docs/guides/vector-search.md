# Vector search

pydynox can store fixed-size embeddings, define DynamoDB vector indexes, and
run similarity searches through the model or client APIs. It stores and
searches vectors; it does not generate embeddings.

## Define a vector model

Use `VectorAttribute` for the embedding and `VectorIndex` for the search
configuration:

=== "vector_search.py"
    ```python
    --8<-- "docs/examples/vector/vector_search.py"
    ```

`dimensions` must match the embedding model output. The attribute accepts
sequences of integers or floats and objects with a one-dimensional
`tolist()` result.

## Vector index options

```python
semantic = VectorIndex(
    index_name="semantic-index",
    vector_attribute="embedding",
    distance=VectorDistance.COSINE,
    partition_key="tenant_id",
    inline_filters=["category"],
    projection=["name", "category"],
)
```

| Option | Description |
|--------|-------------|
| `index_name` | DynamoDB vector index name |
| `vector_attribute` | Model attribute containing the vector |
| `distance` | `COSINE`, `EUCLIDEAN`, or `DOT_PRODUCT` |
| `partition_key` | Optional vector partition key |
| `inline_filters` | Attributes allowed in search filters |
| `projection` | `"ALL"`, `"KEYS_ONLY"`, or a list of attributes |

Aliases are applied when pydynox builds the index definition and search
expressions.

## Create the table

Declared vector indexes are included in model table creation:

```python
await Product.create_table(wait=True)
```

Vector indexes require `PAY_PER_REQUEST` billing. Passing
`billing_mode="PROVISIONED"` fails before the request is sent.

With `wait=True`, pydynox waits for the table and vector indexes to become
active and for index backfill to finish.

## Search

Async is the default API:

```python
matches = await Product.semantic.search(
    query_vector,
    partition_key="TENANT#acme",
    where=Product.category == "books",
    top_k=10,
)

for match in matches:
    print(match.item.name, match.score)
```

Use the `sync_` prefix in synchronous code:

```python
matches = Product.semantic.sync_search(
    query_vector,
    partition_key="TENANT#acme",
    where=Product.category == "books",
    top_k=10,
)
```

If an index defines `partition_key`, every search must provide a value. An
index without a vector partition key searches the complete index.

`top_k` must be between 1 and 100. Results preserve the score and ordering
returned by DynamoDB:

```python
match = matches[0]
match.item
match.score

matches.metrics.duration_ms
matches.metrics.request_id
matches.metrics.vector_search_bytes
```

For cosine and Euclidean distance, smaller scores are closer. For dot product,
larger scores rank first.

## Inline filters

`where` uses the normal pydynox condition API:

```python
matches = await Product.semantic.search(
    query_vector,
    partition_key="TENANT#acme",
    where=(Product.category == "books") & (Product.language == "en"),
)
```

The initial filter support accepts:

- Equality comparisons
- `AND` combinations
- Top-level attributes
- Attributes declared in `inline_filters`

Unsupported expressions fail locally before pydynox sends a request.

## Partial projections

Search returns model instances by default. Use `as_dict=True` when the index
projection does not contain every field required to construct the model:

```python
matches = await Product.semantic.search(
    query_vector,
    partition_key="TENANT#acme",
    top_k=5,
    as_dict=True,
)

print(matches[0].item["name"])
```

## Existing tables

Create, inspect, or delete a declared vector index on an existing table:

```python
await Product.semantic.create(wait=True)

info = await Product.semantic.describe()
print(info.status)
print(info.backfilling)
print(info.item_count)
print(info.size_bytes)

await Product.semantic.delete(wait=True)
```

Sync equivalents are available:

```python
Product.semantic.sync_create(wait=True)
info = Product.semantic.sync_describe()
Product.semantic.sync_delete(wait=True)
```

## Client-level API

Use `DynamoDBClient` directly when no model is involved:

```python
result = await client.search_vectors(
    table="products",
    index_name="semantic-index",
    vector=query_vector,
    top_k=10,
    search_condition_expression="#tenant = :tenant",
    expression_attribute_names={"#tenant": "tenant_id"},
    expression_attribute_values={":tenant": "TENANT#acme"},
    projection_expression="pk, #name",
)
```

`sync_search_vectors()` provides the synchronous equivalent. Client-level
matches contain dictionaries instead of model instances.

## Testing

`MemoryBackend` performs exact vector search without DynamoDB:

```python
from pydynox.testing import MemoryBackend


with MemoryBackend():
    Product(
        pk="PRODUCT#1",
        tenant_id="TENANT#acme",
        category="books",
        embedding=[1.0, 0.0],
    ).sync_save()

    matches = Product.semantic.sync_search(
        [0.9, 0.1],
        partition_key="TENANT#acme",
        top_k=1,
    )

    assert matches[0].item.pk == "PRODUCT#1"
```

The memory backend supports cosine distance, Euclidean distance, dot product,
partition keys, equality filters, projections, and `top_k`.

## Validation and limits

- Dimensions: 1 to 4096
- `top_k`: 1 to 100
- Inline filters: up to 18 per index
- Vector indexes per table: 5 by default
- Vector values: finite numbers representable as float32
- Capacity mode: on-demand
- Search consistency: eventual
- Search pagination: not supported
- Search response size: up to 16 MB

Applications need `dynamodb:SearchVectors` permission for searches and the
normal DynamoDB table permissions for index lifecycle and writes.

Vector search and vector index writes are billed by their dedicated byte
capacity metrics. See the
[DynamoDB pricing page](https://aws.amazon.com/dynamodb/pricing/) for current
rates.

## Next steps

- [Attribute types](attributes.md) - Vector validation and aliases
- [Operations metrics](operations-metrics.md) - Search and write capacity
- [Testing](testing.md) - Exact in-memory vector search
