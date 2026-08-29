"""Unit tests for VectorAttribute."""

import math

import pytest
from pydynox import Model, ModelConfig
from pydynox.attributes import StringAttribute, VectorAttribute


class Document(Model):
    model_config = ModelConfig(table="documents")

    pk = StringAttribute(partition_key=True)
    embedding = VectorAttribute(dimensions=3, alias="emb")


def test_vector_attribute_validates_dimensions() -> None:
    with pytest.raises(ValueError, match="between 1 and 4096"):
        VectorAttribute(dimensions=0)

    with pytest.raises(ValueError, match="between 1 and 4096"):
        VectorAttribute(dimensions=4097)


def test_vector_attribute_normalizes_float32() -> None:
    document = Document(pk="DOC#1", embedding=[1, 0.2, -3.5])

    assert document.embedding is not None
    assert document.embedding[0] == 1.0
    assert document.to_dict()["emb"] == document.embedding


def test_vector_attribute_rejects_wrong_dimension_count() -> None:
    with pytest.raises(ValueError, match="requires 3 dimensions, got 2"):
        Document(pk="DOC#1", embedding=[1.0, 2.0])


@pytest.mark.parametrize("value", [True, "1", None])
def test_vector_attribute_rejects_non_numeric_values(value: object) -> None:
    with pytest.raises(TypeError, match="requires numeric values"):
        Document(pk="DOC#1", embedding=[1.0, value, 3.0])


@pytest.mark.parametrize("value", [math.nan, math.inf, -math.inf])
def test_vector_attribute_rejects_non_finite_values(value: float) -> None:
    with pytest.raises(ValueError, match="non-finite"):
        Document(pk="DOC#1", embedding=[1.0, value, 3.0])


def test_vector_attribute_accepts_tolist_objects() -> None:
    class ArrayLike:
        def tolist(self) -> list[float]:
            return [1.0, 2.0, 3.0]

    document = Document(pk="DOC#1", embedding=ArrayLike())  # type: ignore[arg-type]

    assert document.embedding == [1.0, 2.0, 3.0]
