"""Unit tests for field projections."""

from pydynox.client._crud import _build_projection


def test_build_projection_none():
    """Test that None projection returns None."""
    expr, names = _build_projection(None)
    assert expr is None
    assert names is None


def test_build_projection_empty_list():
    """Test that empty list returns None."""
    expr, names = _build_projection([])
    assert expr is None
    assert names is None


def test_build_projection_single_field():
    """Test projection with a single field."""
    expr, names = _build_projection(["name"])
    assert expr == "#p0"
    assert names == {"#p0": "name"}


def test_build_projection_multiple_fields():
    """Test projection with multiple fields."""
    expr, names = _build_projection(["name", "email", "age"])
    assert expr == "#p0, #p1, #p2"
    assert names == {"#p0": "name", "#p1": "email", "#p2": "age"}


def test_build_projection_nested_field():
    """Test projection with nested field using dot notation."""
    expr, names = _build_projection(["address.city"])
    assert expr == "#p0.#p1"
    assert names == {"#p0": "address", "#p1": "city"}


def test_build_projection_mixed_fields():
    """Test projection with both simple and nested fields."""
    expr, names = _build_projection(["name", "address.city", "address.zip"])
    assert expr == "#p0, #p1.#p2, #p3.#p4"
    assert names == {
        "#p0": "name",
        "#p1": "address",
        "#p2": "city",
        "#p3": "address",
        "#p4": "zip",
    }


def test_build_projection_deeply_nested():
    """Test projection with deeply nested field."""
    expr, names = _build_projection(["data.user.profile.name"])
    assert expr == "#p0.#p1.#p2.#p3"
    assert names == {"#p0": "data", "#p1": "user", "#p2": "profile", "#p3": "name"}
