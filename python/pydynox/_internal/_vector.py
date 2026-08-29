"""Internal vector index implementation."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING, Any, Generic, TypeVar

from pydynox._internal._conditions import ConditionAnd, ConditionComparison
from pydynox.attributes.vector import VectorAttribute

if TYPE_CHECKING:
    from pydynox._internal._metrics import OperationMetrics
    from pydynox.conditions import Condition
    from pydynox.model import Model

M = TypeVar("M", bound="Model")
T = TypeVar("T")


class VectorDistance(StrEnum):
    """Distance functions supported by DynamoDB vector indexes."""

    COSINE = "COSINE"
    EUCLIDEAN = "EUCLIDEAN"
    DOT_PRODUCT = "DOT_PRODUCT"


@dataclass(frozen=True)
class VectorMatch(Generic[T]):
    """One item returned by a vector search."""

    item: T
    score: float


class VectorSearchResult(list[VectorMatch[T]], Generic[T]):
    """Vector matches with operation metrics."""

    def __init__(
        self,
        matches: list[VectorMatch[T]],
        metrics: OperationMetrics,
    ) -> None:
        super().__init__(matches)
        self.metrics = metrics


@dataclass(frozen=True)
class VectorIndexInfo:
    """Current state of a DynamoDB vector index."""

    index_name: str
    status: str | None
    backfilling: bool | None
    item_count: int | None
    size_bytes: int | None
    index_arn: str | None
    dimensions: int | None
    distance: VectorDistance | None

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> VectorIndexInfo:
        raw_distance = value.get("distance")
        return cls(
            index_name=value["index_name"],
            status=value.get("status"),
            backfilling=value.get("backfilling"),
            item_count=value.get("item_count"),
            size_bytes=value.get("size_bytes"),
            index_arn=value.get("index_arn"),
            dimensions=value.get("dimensions"),
            distance=VectorDistance(raw_distance) if raw_distance else None,
        )


class VectorIndex(Generic[M]):
    """A DynamoDB vector index bound to a model."""

    def __init__(
        self,
        index_name: str,
        vector_attribute: str,
        *,
        distance: VectorDistance | str = VectorDistance.COSINE,
        partition_key: str | None = None,
        inline_filters: list[str] | None = None,
        projection: str | list[str] = "ALL",
    ) -> None:
        if not index_name:
            raise ValueError("index_name is required")
        if not vector_attribute:
            raise ValueError("vector_attribute is required")

        self.index_name = index_name
        self.vector_attribute = vector_attribute
        self.distance = VectorDistance(distance)
        self.partition_key = partition_key
        self.inline_filters = list(inline_filters or [])
        self.projection = projection

        if len(self.inline_filters) > 18:
            raise ValueError(f"Vector index '{index_name}' supports at most 18 inline filters")
        if len(set(self.inline_filters)) != len(self.inline_filters):
            raise ValueError(f"Vector index '{index_name}' contains duplicate inline filters")
        if partition_key is not None and partition_key in self.inline_filters:
            raise ValueError(
                f"Vector index '{index_name}' cannot use '{partition_key}' as both "
                "partition key and inline filter"
            )
        if not (projection in ("ALL", "KEYS_ONLY") or isinstance(projection, list)):
            raise ValueError("projection must be 'ALL', 'KEYS_ONLY', or a list of attributes")
        if isinstance(projection, list) and not projection:
            raise ValueError("projection attribute list cannot be empty")
        if isinstance(projection, list) and len(set(projection)) != len(projection):
            raise ValueError(
                f"Vector index '{index_name}' contains duplicate projection attributes"
            )

        self._model_class: type[M] | None = None
        self._attr_name: str | None = None

    def __set_name__(self, owner: type[M], name: str) -> None:
        self._attr_name = name

    def _clone_unbound(self) -> VectorIndex[M]:
        """Return an independent descriptor for an inherited model."""
        return VectorIndex(
            index_name=self.index_name,
            vector_attribute=self.vector_attribute,
            distance=self.distance,
            partition_key=self.partition_key,
            inline_filters=self.inline_filters,
            projection=(
                list(self.projection) if isinstance(self.projection, list) else self.projection
            ),
        )

    def _bind_to_model(self, model_class: type[M]) -> None:
        attributes = model_class._attributes
        vector_attr = attributes.get(self.vector_attribute)
        if vector_attr is None:
            raise ValueError(
                f"Vector index '{self.index_name}' references unknown attribute "
                f"'{self.vector_attribute}'"
            )
        if not isinstance(vector_attr, VectorAttribute):
            raise ValueError(
                f"Vector index '{self.index_name}' attribute '{self.vector_attribute}' "
                "must be a VectorAttribute"
            )
        if self.partition_key == self.vector_attribute:
            raise ValueError(
                f"Vector index '{self.index_name}' cannot use its vector attribute "
                "as the partition key"
            )
        if self.vector_attribute in self.inline_filters:
            raise ValueError(
                f"Vector index '{self.index_name}' cannot use its vector attribute "
                "as an inline filter"
            )

        search_schema_attributes = [
            value for value in [self.partition_key, *self.inline_filters] if value is not None
        ]
        referenced = list(search_schema_attributes)
        if isinstance(self.projection, list):
            referenced.extend(self.projection)
        for attr_name in referenced:
            if attr_name not in attributes:
                raise ValueError(
                    f"Vector index '{self.index_name}' references unknown attribute '{attr_name}'"
                )
        for attr_name in search_schema_attributes:
            attr_type = attributes[attr_name].attr_type
            if attr_type not in {"S", "N", "B"}:
                raise ValueError(
                    f"Vector index '{self.index_name}' search schema attribute "
                    f"'{attr_name}' must use scalar DynamoDB type S, N, or B"
                )

        self._model_class = model_class

    def _get_model_class(self) -> type[M]:
        if self._model_class is None:
            raise RuntimeError(f"Vector index '{self.index_name}' is not bound to a model")
        return self._model_class

    def to_create_table_definition(self, model_class: type[M]) -> dict[str, Any]:
        vector_attr = model_class._attributes[self.vector_attribute]
        assert isinstance(vector_attr, VectorAttribute)

        result: dict[str, Any] = {
            "index_name": self.index_name,
            "vector_attribute": model_class._py_to_dynamo.get(
                self.vector_attribute, self.vector_attribute
            ),
            "dimensions": vector_attr.dimensions,
            "distance_function": self.distance.value,
            "attribute_definitions": [
                (
                    model_class._py_to_dynamo.get(name, name),
                    model_class._attributes[name].attr_type,
                )
                for name in [self.partition_key, *self.inline_filters]
                if name is not None
            ],
            "table_key_attributes": [
                model_class._py_to_dynamo.get(name, name)
                for name in [model_class._partition_key, model_class._sort_key]
                if name is not None
            ],
        }

        if self.partition_key is not None:
            result["partition_key"] = model_class._py_to_dynamo.get(
                self.partition_key, self.partition_key
            )
        if self.inline_filters:
            result["inline_filters"] = [
                model_class._py_to_dynamo.get(name, name) for name in self.inline_filters
            ]

        if isinstance(self.projection, list):
            result["projection"] = "INCLUDE"
            result["non_key_attributes"] = [
                model_class._py_to_dynamo.get(name, name) for name in self.projection
            ]
        else:
            result["projection"] = self.projection

        return result

    def _validate_filter(self, condition: Condition) -> None:
        allowed = {
            self._get_model_class()._py_to_dynamo.get(name, name) for name in self.inline_filters
        }

        def visit(node: Any) -> None:
            if isinstance(node, ConditionAnd):
                visit(node.left)
                visit(node.right)
                return
            if not isinstance(node, ConditionComparison) or node.operator != "=":
                raise ValueError("Vector search filters support equality comparisons joined by AND")
            if len(node.path.path) != 1 or node.path.path[0] not in allowed:
                name = node.path.path[0] if node.path.path else "<unknown>"
                raise ValueError(f"Filter attribute '{name}' is not declared as an inline filter")

        visit(condition)

    def _serialize_filter(
        self,
        condition: Condition,
        names: dict[str, str],
        values: dict[str, Any],
    ) -> str:
        if isinstance(condition, ConditionAnd):
            left = self._serialize_filter(condition.left, names, values)
            right = self._serialize_filter(condition.right, names, values)
            return f"({left} AND {right})"

        assert isinstance(condition, ConditionComparison)
        attribute = condition.path.attribute
        assert attribute is not None
        path = condition.path._serialize_path(names)
        placeholder = f":v{len(values)}"
        values[placeholder] = attribute.serialize(condition.value)
        return f"{path} = {placeholder}"

    def _prepare_projection(
        self,
        names: dict[str, str],
        as_dict: bool,
    ) -> str | None:
        if as_dict:
            return None

        model_class = self._get_model_class()
        if self.projection == "ALL":
            selected = set(model_class._attributes)
        else:
            selected = {
                name
                for name in [
                    model_class._partition_key,
                    model_class._sort_key,
                    self.vector_attribute,
                    self.partition_key,
                    *self.inline_filters,
                ]
                if name is not None
            }
            if isinstance(self.projection, list):
                selected.update(self.projection)

        missing_required = [
            name
            for name, attribute in model_class._attributes.items()
            if attribute.required and name not in selected
        ]
        if missing_required:
            missing = ", ".join(sorted(missing_required))
            raise ValueError(
                f"Vector index '{self.index_name}' projection does not include required "
                f"model attributes: {missing}. Use as_dict=True or include them in the projection"
            )

        placeholders: list[str] = []
        for name in model_class._attributes:
            if name not in selected:
                continue
            dynamo_name = model_class._py_to_dynamo.get(name, name)
            placeholder = names.get(dynamo_name)
            if placeholder is None:
                placeholder = f"#vector_projection_{len(placeholders)}"
                names[dynamo_name] = placeholder
            placeholders.append(placeholder)
        return ", ".join(placeholders)

    def _prepare_search(
        self,
        query_vector: Any,
        partition_key: Any,
        where: Condition | None,
        top_k: int,
        as_dict: bool = False,
    ) -> tuple[
        list[float],
        str | None,
        dict[str, str] | None,
        dict[str, Any] | None,
        str | None,
    ]:
        model_class = self._get_model_class()
        vector_attr = model_class._attributes[self.vector_attribute]
        assert isinstance(vector_attr, VectorAttribute)
        vector = vector_attr.serialize(query_vector)
        assert vector is not None

        if isinstance(top_k, bool) or not isinstance(top_k, int) or not 1 <= top_k <= 100:
            raise ValueError("top_k must be between 1 and 100")
        if self.partition_key is not None and partition_key is None:
            raise ValueError(
                f"Vector index '{self.index_name}' requires partition_key='{self.partition_key}'"
            )
        if self.partition_key is None and partition_key is not None:
            raise ValueError(f"Vector index '{self.index_name}' does not define a partition key")

        names: dict[str, str] = {}
        values: dict[str, Any] = {}
        expressions: list[str] = []

        if self.partition_key is not None:
            dynamo_name = model_class._py_to_dynamo.get(self.partition_key, self.partition_key)
            names[dynamo_name] = "#vector_pk"
            values[":vector_pk"] = model_class._attributes[self.partition_key].serialize(
                partition_key
            )
            expressions.append("#vector_pk = :vector_pk")

        if where is not None:
            self._validate_filter(where)
            expressions.append(self._serialize_filter(where, names, values))

        expression = " AND ".join(expressions) if expressions else None
        projection_expression = self._prepare_projection(names, as_dict)
        attr_names = {placeholder: name for name, placeholder in names.items()} if names else None
        return vector, expression, attr_names, values or None, projection_expression

    def _convert_result(
        self,
        result: VectorSearchResult[dict[str, Any]],
        as_dict: bool,
    ) -> VectorSearchResult[M] | VectorSearchResult[dict[str, Any]]:
        if as_dict:
            return result

        model_class = self._get_model_class()
        matches = [
            VectorMatch(item=model_class.from_dict(match.item), score=match.score)
            for match in result
        ]
        return VectorSearchResult(matches, result.metrics)

    async def search(
        self,
        query_vector: Any,
        *,
        partition_key: Any = None,
        where: Condition | None = None,
        top_k: int = 10,
        as_dict: bool = False,
    ) -> VectorSearchResult[M] | VectorSearchResult[dict[str, Any]]:
        model_class = self._get_model_class()
        vector, expression, names, values, projection = self._prepare_search(
            query_vector, partition_key, where, top_k, as_dict
        )
        result = await model_class._get_client().search_vectors(
            model_class._get_table(),
            self.index_name,
            vector,
            top_k=top_k,
            search_condition_expression=expression,
            expression_attribute_names=names,
            expression_attribute_values=values,
            projection_expression=projection,
        )
        return self._convert_result(result, as_dict)

    def sync_search(
        self,
        query_vector: Any,
        *,
        partition_key: Any = None,
        where: Condition | None = None,
        top_k: int = 10,
        as_dict: bool = False,
    ) -> VectorSearchResult[M] | VectorSearchResult[dict[str, Any]]:
        model_class = self._get_model_class()
        vector, expression, names, values, projection = self._prepare_search(
            query_vector, partition_key, where, top_k, as_dict
        )
        result = model_class._get_client().sync_search_vectors(
            model_class._get_table(),
            self.index_name,
            vector,
            top_k=top_k,
            search_condition_expression=expression,
            expression_attribute_names=names,
            expression_attribute_values=values,
            projection_expression=projection,
        )
        return self._convert_result(result, as_dict)

    async def create(
        self,
        *,
        wait: bool = False,
        timeout_seconds: int | None = None,
    ) -> None:
        model_class = self._get_model_class()
        await model_class._get_client().create_vector_index(
            model_class._get_table(),
            self.to_create_table_definition(model_class),
            wait=wait,
            timeout_seconds=timeout_seconds,
        )

    def sync_create(
        self,
        *,
        wait: bool = False,
        timeout_seconds: int | None = None,
    ) -> None:
        model_class = self._get_model_class()
        model_class._get_client().sync_create_vector_index(
            model_class._get_table(),
            self.to_create_table_definition(model_class),
            wait=wait,
            timeout_seconds=timeout_seconds,
        )

    async def delete(
        self,
        *,
        wait: bool = False,
        timeout_seconds: int | None = None,
    ) -> None:
        model_class = self._get_model_class()
        await model_class._get_client().delete_vector_index(
            model_class._get_table(),
            self.index_name,
            wait=wait,
            timeout_seconds=timeout_seconds,
        )

    def sync_delete(
        self,
        *,
        wait: bool = False,
        timeout_seconds: int | None = None,
    ) -> None:
        model_class = self._get_model_class()
        model_class._get_client().sync_delete_vector_index(
            model_class._get_table(),
            self.index_name,
            wait=wait,
            timeout_seconds=timeout_seconds,
        )

    async def describe(self) -> VectorIndexInfo:
        model_class = self._get_model_class()
        value = await model_class._get_client().describe_vector_index(
            model_class._get_table(), self.index_name
        )
        return VectorIndexInfo.from_dict(value)

    def sync_describe(self) -> VectorIndexInfo:
        model_class = self._get_model_class()
        value = model_class._get_client().sync_describe_vector_index(
            model_class._get_table(), self.index_name
        )
        return VectorIndexInfo.from_dict(value)
