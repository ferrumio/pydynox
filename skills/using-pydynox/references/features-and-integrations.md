# Model features and integrations

Choose features from the application's requirements. These notes identify the
pydynox API and behavior to check before implementing them; the linked guides
contain maintained Python examples.

## Schema and values

| Need | API and decision |
|------|------------------|
| Exact scalar decimal | `DecimalAttribute`; create fractions from decimal strings, not floats |
| Readable Python names, different stored names | Attribute `alias=...`; model calls use Python field names, `to_dict()` uses stored names |
| Compound single-table keys | `StringAttribute(template="CUSTOMER#{customer_id}")`; match the deployed schema and key ordering |
| Automatic IDs or timestamps | `AutoGenerate` strategies; check creation versus update timing |
| Nested data | `MapAttribute` / `ListAttribute`; check partial and atomic update behavior |
| Several entity types in one table | Key templates and model inheritance; keep each entity's key prefix and read path explicit |

`DecimalAttribute` is model-specific. Raw client reads do not inherit model
conversion rules, and nested map/list values are not converted by a scalar
Decimal field. Keep those boundaries explicit when mixing clients and models.

Read [attributes](https://ferrumio.github.io/pydynox/guides/attributes/),
[aliases](https://ferrumio.github.io/pydynox/guides/aliases/),
[auto-generation](https://ferrumio.github.io/pydynox/guides/auto-generate/),
[single-table design](https://ferrumio.github.io/pydynox/guides/single-table/), and
[inheritance](https://ferrumio.github.io/pydynox/guides/inheritance/).

## Expiry, concurrent edits, and hooks

Use `TTLAttribute` with `ExpiresIn.hours(...)` or the documented datetime input.
The table's TTL setting must use the stored attribute name, including an alias.
DynamoDB deletion is asynchronous; sessions or leases that must reject an
expired item should check `is_expired` when reading it. Verify whether a TTL
helper only changes the model or also persists the change before returning.

Loaded models use smart save: `save()` writes changed fields, while
`full_replace=True` requests a full replacement. Smart save alone does not
detect that another writer changed the same field.

Add `VersionAttribute` for optimistic locking. Catch
`ConditionalCheckFailedException`, reload the current item, reapply the
business operation, and retry with a bound when a retry is appropriate.
Repeatedly saving the same stale instance cannot resolve a version conflict.
For a simple counter, an atomic increment may avoid the read/retry cycle.

Hooks come from `pydynox.hooks`, including `before_save`, `after_save`,
`before_update`, and `after_load`. Match the hook to the operation; update and
save have separate lifecycle events. A post-write side effect can fail after
the database write has succeeded, so avoid treating it as part of the same
atomic commit.

Read [TTL](https://ferrumio.github.io/pydynox/guides/ttl/),
[smart save](https://ferrumio.github.io/pydynox/guides/smart-save/),
[optimistic locking](https://ferrumio.github.io/pydynox/guides/optimistic-locking/),
[hooks](https://ferrumio.github.io/pydynox/guides/hooks/), and
[distributed locks](https://ferrumio.github.io/pydynox/guides/distributed-locks/).

## Existing application schemas

The public `dynamodb_model` decorator can attach DynamoDB behavior to Pydantic
models and dataclasses. Configure its `table`, `partition_key`, optional
`sort_key`, and client. Do not replace the application's schema with a second
ORM model unless the application needs a separate persistence representation.

Pydantic is an optional dependency. Check the application's installed extra
and version before suggesting Pydantic-specific code.

Read [Pydantic](https://ferrumio.github.io/pydynox/guides/pydantic/) and
[dataclasses](https://ferrumio.github.io/pydynox/guides/dataclass/).

## Large values, encryption, and specialized operations

| Task | Read and verify |
|------|-----------------|
| Large text or item size planning | [Attributes](https://ferrumio.github.io/pydynox/guides/attributes/) and [size calculator](https://ferrumio.github.io/pydynox/guides/size-calculator/) |
| Files in S3 linked from a model | [S3Attribute](https://ferrumio.github.io/pydynox/guides/s3-attribute/): bucket, object lifecycle, upload/download methods, and write-operation support |
| KMS-backed encrypted fields | [Encryption](https://ferrumio.github.io/pydynox/guides/encryption/): key, permissions, context, and attribute behavior |
| SQL-like statements | [PartiQL](https://ferrumio.github.io/pydynox/guides/partiql/): parameters and result/pagination contract |
| Vector search | [Vector search](https://ferrumio.github.io/pydynox/guides/vector-search/): index availability, distance, dimensions, and installed API |

S3 and KMS add service calls and permissions. A DynamoDB transaction does not
make an external service call part of its atomic commit. Check the transaction
guide's supported attributes before queuing a model with those features.
