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
    op = User.name.set("John")
    expr, names, values = serialize_atomic([op])

    assert "SET" in expr
    assert "#n0 = :v0" in expr
    assert names["name"] == "#n0"
    assert values[":v0"] == "John"


def test_add():
    op = User.count.add(1)
    expr, names, values = serialize_atomic([op])

    assert "SET" in expr
    assert "#n0 = #n0 + :v0" in expr
    assert names["count"] == "#n0"
    assert values[":v0"] == 1


def test_add_negative():
    op = User.count.add(-5)
    expr, names, values = serialize_atomic([op])

    assert "#n0 = #n0 + :v0" in expr
    assert values[":v0"] == -5


def test_remove():
    op = User.name.remove()
    expr, names, values = serialize_atomic([op])

    assert "REMOVE" in expr
    assert "#n0" in expr
    assert names["name"] == "#n0"
    assert len(values) == 0


def test_append():
    op = User.tags.append(["new", "items"])
    expr, names, values = serialize_atomic([op])

    assert "SET" in expr
    assert "list_append(#n0, :v0)" in expr
    assert names["tags"] == "#n0"
    assert values[":v0"] == ["new", "items"]


def test_prepend():
    op = User.tags.prepend(["first"])
    expr, names, values = serialize_atomic([op])

    assert "SET" in expr
    assert "list_append(:v0, #n0)" in expr
    assert values[":v0"] == ["first"]


def test_if_not_exists():
    op = User.count.if_not_exists(0)
    expr, names, values = serialize_atomic([op])

    assert "SET" in expr
    assert "if_not_exists(#n0, :v0)" in expr
    assert values[":v0"] == 0


def test_multiple_set_operations():
    ops = [
        User.name.set("John"),
        User.age.set(30),
    ]
    expr, names, values = serialize_atomic(ops)

    assert "SET" in expr
    assert "#n0 = :v0" in expr
    assert "#n1 = :v1" in expr
    assert values[":v0"] == "John"
    assert values[":v1"] == 30


def test_mixed_set_and_remove():
    ops = [
        User.name.set("John"),
        User.age.remove(),
    ]
    expr, names, values = serialize_atomic(ops)

    assert "SET" in expr
    assert "REMOVE" in expr
    assert "#n0 = :v0" in expr
    assert "#n1" in expr


def test_multiple_removes():
    ops = [
        User.name.remove(),
        User.age.remove(),
    ]
    expr, names, values = serialize_atomic(ops)

    assert "REMOVE" in expr
    assert "#n0" in expr
    assert "#n1" in expr
    assert "SET" not in expr


def test_complex_combination():
    ops = [
        User.count.add(1),
        User.tags.append(["verified"]),
        User.name.remove(),
    ]
    expr, names, values = serialize_atomic(ops)

    assert "SET" in expr
    assert "REMOVE" in expr
    assert len(values) == 2
