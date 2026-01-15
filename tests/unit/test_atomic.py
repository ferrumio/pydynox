"""Unit tests for atomic update operations."""

from pydynox import Model, ModelConfig
from pydynox._internal._atomic import serialize_atomic
from pydynox.attributes import ListAttribute, NumberAttribute, StringAttribute


class User(Model):
    model_config = ModelConfig(table="users")

    pk = StringAttribute(hash_key=True)
    name = StringAttribute()
    age = NumberAttribute()
    count = NumberAttribute()
    tags = ListAttribute()


def test_set():
    """Test SET operation for atomic updates."""
    # GIVEN a set operation on name attribute
    op = User.name.set("John")

    # WHEN we serialize the operation
    expr, names, values = serialize_atomic([op])

    # THEN the expression should contain SET with correct placeholders
    assert "SET" in expr
    assert "#n0 = :v0" in expr
    assert names["name"] == "#n0"
    assert values[":v0"] == "John"


def test_add():
    """Test ADD operation for atomic updates."""
    # GIVEN an add operation on count attribute
    op = User.count.add(1)

    # WHEN we serialize the operation
    expr, names, values = serialize_atomic([op])

    # THEN the expression should use addition syntax
    assert "SET" in expr
    assert "#n0 = #n0 + :v0" in expr
    assert names["count"] == "#n0"
    assert values[":v0"] == 1


def test_add_negative():
    """Test ADD with negative value for subtraction."""
    # GIVEN an add operation with negative value
    op = User.count.add(-5)

    # WHEN we serialize the operation
    expr, names, values = serialize_atomic([op])

    # THEN the expression should use the negative value
    assert "#n0 = #n0 + :v0" in expr
    assert values[":v0"] == -5


def test_remove():
    """Test REMOVE operation for atomic updates."""
    # GIVEN a remove operation on name attribute
    op = User.name.remove()

    # WHEN we serialize the operation
    expr, names, values = serialize_atomic([op])

    # THEN the expression should contain REMOVE with no values
    assert "REMOVE" in expr
    assert "#n0" in expr
    assert names["name"] == "#n0"
    assert len(values) == 0


def test_append():
    """Test list append operation."""
    # GIVEN an append operation on tags attribute
    op = User.tags.append(["new", "items"])

    # WHEN we serialize the operation
    expr, names, values = serialize_atomic([op])

    # THEN the expression should use list_append function
    assert "SET" in expr
    assert "list_append(#n0, :v0)" in expr
    assert names["tags"] == "#n0"
    assert values[":v0"] == ["new", "items"]


def test_prepend():
    """Test list prepend operation."""
    # GIVEN a prepend operation on tags attribute
    op = User.tags.prepend(["first"])

    # WHEN we serialize the operation
    expr, names, values = serialize_atomic([op])

    # THEN the expression should use list_append with reversed order
    assert "SET" in expr
    assert "list_append(:v0, #n0)" in expr
    assert values[":v0"] == ["first"]


def test_if_not_exists():
    """Test if_not_exists operation."""
    # GIVEN an if_not_exists operation on count attribute
    op = User.count.if_not_exists(0)

    # WHEN we serialize the operation
    expr, names, values = serialize_atomic([op])

    # THEN the expression should use if_not_exists function
    assert "SET" in expr
    assert "if_not_exists(#n0, :v0)" in expr
    assert values[":v0"] == 0


def test_multiple_set_operations():
    """Test multiple SET operations combined."""
    # GIVEN multiple set operations
    ops = [
        User.name.set("John"),
        User.age.set(30),
    ]

    # WHEN we serialize the operations
    expr, names, values = serialize_atomic(ops)

    # THEN both operations should be in the expression
    assert "SET" in expr
    assert "#n0 = :v0" in expr
    assert "#n1 = :v1" in expr
    assert values[":v0"] == "John"
    assert values[":v1"] == 30


def test_mixed_set_and_remove():
    """Test mixed SET and REMOVE operations."""
    # GIVEN a set and a remove operation
    ops = [
        User.name.set("John"),
        User.age.remove(),
    ]

    # WHEN we serialize the operations
    expr, names, values = serialize_atomic(ops)

    # THEN both SET and REMOVE should be in the expression
    assert "SET" in expr
    assert "REMOVE" in expr
    assert "#n0 = :v0" in expr
    assert "#n1" in expr


def test_multiple_removes():
    """Test multiple REMOVE operations."""
    # GIVEN multiple remove operations
    ops = [
        User.name.remove(),
        User.age.remove(),
    ]

    # WHEN we serialize the operations
    expr, names, values = serialize_atomic(ops)

    # THEN only REMOVE should be in the expression
    assert "REMOVE" in expr
    assert "#n0" in expr
    assert "#n1" in expr
    assert "SET" not in expr


def test_complex_combination():
    """Test complex combination of operations."""
    # GIVEN a mix of add, append, and remove operations
    ops = [
        User.count.add(1),
        User.tags.append(["verified"]),
        User.name.remove(),
    ]

    # WHEN we serialize the operations
    expr, names, values = serialize_atomic(ops)

    # THEN all operation types should be present
    assert "SET" in expr
    assert "REMOVE" in expr
    assert len(values) == 2
