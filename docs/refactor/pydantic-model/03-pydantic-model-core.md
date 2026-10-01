# PR 3: `PydanticModel` core + combined metaclass

**Summary**: introduce the opt-in `PydanticModel(Model, BaseModel)` class with
`_PydanticModelMeta`, wire DynamoDB schema from Pydantic `model_fields` +
PR 2 markers, and prove a minimal save/get vertical slice. **Pair with
maintainer on metaclass wiring before opening upstream.**

## Motivation

This is the deliverable that unblocks everything else. Once `PydanticModel`
exists:

- `Annotated[T, Dynamo.*]` markers have a real consumer.
- Config naming (`dynamodb_config` vs `model_config`) is scoped to this class.
- `@dynamodb_model` has a migration target (PR 7).

The hard part is metaclass cooperation: Pydantic's `ModelMetaclass` must run
first to populate `model_fields`, then pydynox must populate the same class
dunders that CRUD, indexes, transactions, and batch read today.

## Scope

In:

- New module
  [python/pydynox/pydantic_model.py](../../../python/pydynox/pydantic_model.py):
  - Lazy pydantic import; clear `ImportError` naming `pip install pydynox[pydantic]`.
  - `_PydanticModelMeta(ModelMeta, ModelMetaclass)`.
  - `_collect_dynamodb_schema(cls)` walking `cls.model_fields`, reading
    `FieldInfo.metadata` for `Dynamo.*` markers, calling PR 2 builder.
  - Reuse PR 1 helpers for indexes, hooks, discriminator.
  - `PydanticModel(Model, BaseModel)` with:
    - `dynamodb_config: ClassVar[ModelConfig]` for table/client settings.
    - Default `model_config = ConfigDict(validate_assignment=True, ...)`.
- Lazy export from [python/pydynox/__init__.py](../../../python/pydynox/__init__.py).
- Minimal docs snippet in a new `docs/guides/pydantic.md` (expanded later).
- Tests: import guards; metaclass dunders; one save/get with partition key +
  primitive fields.

Out (follow-up PRs):

- `cls.F` namespace (PR 4).
- Dirty tracking / `to_dict` / `from_dict` shims (PR 5).
- Full parity matrix (PR 6).
- Deprecating `@dynamodb_model` (PR 7).

## Metaclass wiring

```python
from pydantic._internal._model_construction import ModelMetaclass
from pydynox._internal._model._base import ModelMeta

class _PydanticModelMeta(ModelMeta, ModelMetaclass):
    def __new__(mcs, name, bases, namespace, **kwargs):
        # 1. Pydantic first: model_fields, validators, ConfigDict.
        cls = ModelMetaclass.__new__(mcs, name, bases, namespace, **kwargs)

        # 2. Skip base PydanticModel class itself.
        if name == "PydanticModel" and namespace.get("__module__") == "pydynox.pydantic_model":
            return cls

        # 3. DynamoDB schema from model_fields + Dynamo.* metadata.
        _collect_dynamodb_schema(cls)
        return cls
```

Exact MRO and hook ordering to be validated with maintainer pairing.

## Public API

```python
from typing import Annotated, ClassVar
from pydantic import ConfigDict, Field
from pydynox import PydanticModel, ModelConfig, Dynamo

class User(PydanticModel):
    dynamodb_config: ClassVar[ModelConfig] = ModelConfig(table="users")
    model_config = ConfigDict(validate_assignment=True)

    pk:   Annotated[str, Dynamo.partition_key()]
    name: str = Field(description="Display name")

user = await User(name="Ada").save()
found = await User.get(pk=user.pk)
```

## Back-compat

`Model` unchanged. `import pydynox` without Pydantic installed still works.

## Test plan

- `import pydynox` succeeds without pydantic extra.
- `from pydynox import PydanticModel` without pydantic raises clear
  `ImportError`.
- Subclass dunders: `_attributes`, `_partition_key`, `_py_to_dynamo` match
  expectations for a fixture model.
- Integration: save + get round-trip for primitives (mock or local DynamoDB).

## Size

L. Roughly 200–350 LOC implementation + 150–250 LOC tests.

## Depends on / unblocks

- Depends on: PR 2 (markers); PR 1 strongly recommended.
- Unblocks: PRs 4, 5, 6, 7.

## Maintainer pairing

Schedule a pairing session **before** opening the upstream PR. Focus areas:

- Metaclass MRO and `ModelMetaclass` kwargs forwarding.
- Interaction with user-defined metaclass subclasses.
- Ordering: Pydantic validators vs pydynox hook registration.
