"""CRUD operations type checking example."""

from typing import TYPE_CHECKING, Any

from pydynox import Model, ModelConfig
from pydynox.attributes import StringAttribute
from pydynox.model import ModelQueryResult, ModelScanResult

# Type-only tests - wrapped in TYPE_CHECKING to avoid runtime execution
# These show what types mypy expects


class User(Model):
    model_config = ModelConfig(table="users")

    pk = StringAttribute(hash_key=True)
    sk = StringAttribute(range_key=True)
    name = StringAttribute()


if TYPE_CHECKING:
    user = User(pk="USER#1", sk="PROFILE", name="John")

    # get() returns M | dict[str, Any] | None
    fetched: User | dict[str, Any] | None = User.get(pk="USER#1", sk="PROFILE")

    # save(), delete(), update() return None
    user.save()
    user.delete()
    user.update(name="Jane")

    # query() returns ModelQueryResult[M]
    query_result: ModelQueryResult[User] = User.query(hash_key="USER#1")

    # Iterating - use isinstance to narrow the type
    for item in User.query(hash_key="USER#1"):
        if isinstance(item, User):
            name: str | None = item.name

    # scan() returns ModelScanResult[M]
    scan_result: ModelScanResult[User] = User.scan()

    # batch_get() returns list[M] | list[dict[str, Any]]
    batch: list[User] | list[dict[str, Any]] = User.batch_get([{"pk": "USER#1", "sk": "PROFILE"}])

    # from_dict() returns M
    user_from_dict: User = User.from_dict({"pk": "USER#1", "sk": "PROFILE", "name": "Test"})
