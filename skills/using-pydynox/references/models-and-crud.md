# Models and CRUD

Read [application.py](../examples/application.py) for the `Order` model and
`crud` / `sync_crud` examples.

## Client and schema

`DynamoDBClient(region="us-east-1")` uses the AWS SDK credential chain. A named
profile can be supplied with `profile=...`. Use the application's credential
source; the dummy credentials in the LocalStack example are for local tests.

Models can use the client registered with `set_default_client(client)` or an
explicit `ModelConfig(table=..., client=client)`. Create and reuse clients at
application startup.

Declare a partition key and, when the table has one, a sort key. Match the
existing table's key names and types. `get` and `delete` need the complete key.
Use the model's Python field names when an attribute has an alias.

Choose attributes for the values being stored: `StringAttribute`,
`NumberAttribute`, `BooleanAttribute`, and the documented collection types.
For exact decimal values, see
[DecimalAttribute](https://ferrumio.github.io/pydynox/guides/attributes/).
The example stores integer cents and uses strongly consistent reads so each
read observes the preceding write. Choose consistency for the application's
read requirements.

## Reads and writes

| Intent | Async | Sync |
|--------|-------|------|
| Save a model | `await order.save()` | `order.sync_save()` |
| Read by its full key | `await Order.get(pk=pk, sk=sk)` | `Order.sync_get(pk=pk, sk=sk)` |
| Update selected fields | `await order.update(status="paid")` | `order.sync_update(status="paid")` |
| Delete the item | `await order.delete()` | `order.sync_delete()` |

Handle `None` from `get` before accessing model fields. A missing item and a
missing table are different cases; the latter raises
`ResourceNotFoundException`.

For create-only writes, pass `condition=Order.pk.not_exists()` to `save`.
Use a condition on `update` when a state transition depends on the stored state,
such as `condition=(Order.status == "pending")`. Catch
`ConditionalCheckFailedException` when that conflict is an expected application
outcome.

For an increment, use `await order.update(atomic=[Order.total_cents.add(100)])`
or `order.sync_update(atomic=[Order.total_cents.add(100)])`.
Atomic actions run in DynamoDB and avoid a separate read/modify/write sequence.
See [atomic updates](https://ferrumio.github.io/pydynox/guides/atomic-updates/).

Keep the model and client APIs distinct: `Order.get` takes model key fields;
`client.get_item` takes a table name and a key dictionary.

Further reading:

- [Client configuration](https://ferrumio.github.io/pydynox/guides/client/)
- [Models](https://ferrumio.github.io/pydynox/guides/models/)
- [Aliases](https://ferrumio.github.io/pydynox/guides/aliases/)
- [Exceptions](https://ferrumio.github.io/pydynox/guides/exceptions/)
