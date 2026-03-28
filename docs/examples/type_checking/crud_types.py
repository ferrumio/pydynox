"""CRUD operations type checking example."""

from typing import TYPE_CHECKING, Any

from pydynox import Model, ModelConfig
from pydynox.attributes import StringAttribute
from pydynox.model import (
    AsyncModelQueryResult,
    AsyncModelScanResult,
    ModelQueryResult,
    ModelScanResult,
)

# Type-only tests - wrapped in TYPE_CHECKING to avoid runtime execution
# These show what types mypy expects


class User(Model):
    model_config = ModelConfig(table="users")

    pk = StringAttribute(partition_key=True)
    sk = StringAttribute(sort_key=True)
    name = StringAttribute()


if TYPE_CHECKING:
    user = User(pk="USER#1", sk="PROFILE", name="John")

    # sync_get() without as_dict returns M | None
    fetched: User | None = User.sync_get(pk="USER#1", sk="PROFILE")

    # sync_get() with as_dict=True returns dict[str, Any] | None
    fetched_dict: dict[str, Any] | None = User.sync_get(as_dict=True, pk="USER#1", sk="PROFILE")

    # sync save/delete/update return None
    user.sync_save()
    user.sync_delete()
    user.sync_update(name="Jane")

    # sync_query() returns ModelQueryResult[M], iterating yields M
    query_result: ModelQueryResult[User] = User.sync_query(partition_key="USER#1")

    # Iterating yields User directly - no isinstance needed
    for item in User.sync_query(partition_key="USER#1"):
        name: str | None = item.name

    # sync_query() with as_dict=True returns ModelQueryResult[dict], iterating yields dict
    for row in User.sync_query(partition_key="USER#1", as_dict=True):
        val: Any = row["name"]

    # sync_scan() returns ModelScanResult[M], iterating yields M
    scan_result: ModelScanResult[User] = User.sync_scan()

    # sync_scan() with as_dict=True returns ModelScanResult[dict]
    dict_scan: ModelScanResult[dict[str, Any]] = User.sync_scan(as_dict=True)

    # Async variants use Async* result types
    async_query_result: AsyncModelQueryResult[User] = User.query(partition_key="USER#1")
    async_dict_query: AsyncModelQueryResult[dict[str, Any]] = User.query(
        partition_key="USER#1", as_dict=True
    )
    async_scan_result: AsyncModelScanResult[User] = User.scan()
    async_dict_scan: AsyncModelScanResult[dict[str, Any]] = User.scan(as_dict=True)

    # sync_batch_get() without as_dict returns list[M]
    batch: list[User] = User.sync_batch_get([{"pk": "USER#1", "sk": "PROFILE"}])

    # sync_batch_get() with as_dict=True returns list[dict[str, Any]]
    batch_dict: list[dict[str, Any]] = User.sync_batch_get(
        [{"pk": "USER#1", "sk": "PROFILE"}], as_dict=True
    )

    # from_dict() returns M
    user_from_dict: User = User.from_dict({"pk": "USER#1", "sk": "PROFILE", "name": "Test"})
