"""Unit tests for field projections."""

from pydynox.client._crud import _build_projection


def test_build_projection_none():
    """Test that None projection returns None."""
    # WHEN we build projection with None
    expr, names = _build_projection(None)

    # THEN both should be None
    assert expr is None
    assert names is None


def test_build_projection_empty_list():
    """Test that empty list returns None."""
    # WHEN we build projection with empty list
    expr, names = _build_projection([])

    # THEN both should be None
    assert expr is None
    assert names is None


def test_build_projection_single_field():
    """Test projection with a single field."""
    # WHEN we build projection with single field
    expr, names = _build_projection(["name"])

    # THEN expression and names should be correct
    assert expr == "#p0"
    assert names == {"#p0": "name"}


def test_build_projection_multiple_fields():
    """Test projection with multiple fields."""
    # WHEN we build projection with multiple fields
    expr, names = _build_projection(["name", "email", "age"])

    # THEN all fields should be in expression
    assert expr == "#p0, #p1, #p2"
    assert names == {"#p0": "name", "#p1": "email", "#p2": "age"}


def test_build_projection_nested_field():
    """Test projection with nested field using dot notation."""
    # WHEN we build projection with nested field
    expr, names = _build_projection(["address.city"])

    # THEN nested path should be expanded
    assert expr == "#p0.#p1"
    assert names == {"#p0": "address", "#p1": "city"}


def test_build_projection_mixed_fields():
    """Test projection with both simple and nested fields."""
    # WHEN we build projection with mixed fields
    expr, names = _build_projection(["name", "address.city", "address.zip"])

    # THEN all fields should be handled correctly
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
    # WHEN we build projection with deeply nested field
    expr, names = _build_projection(["data.user.profile.name"])

    # THEN all levels should be expanded
    assert expr == "#p0.#p1.#p2.#p3"
    assert names == {"#p0": "data", "#p1": "user", "#p2": "profile", "#p3": "name"}
