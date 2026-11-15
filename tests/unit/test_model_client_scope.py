"""A cached client belongs to the model class that resolved it (#563).

``_client_instance`` used to be inherited: once the parent resolved its client,
a child that named its own client in ``model_config`` was answered from the
parent's cache, and its own client was never called. These tests pin the cache
to each class, in both call orders and through deeper inheritance.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from pydynox import Model, ModelConfig, clear_default_client, set_default_client
from pydynox.attributes import StringAttribute


def _client() -> MagicMock:
    """A mock DynamoDB client with async and sync reads."""
    client = MagicMock()
    client.get_item = AsyncMock(return_value=None)
    client.sync_get_item = MagicMock(return_value=None)
    client.diagnostics = None
    client._last_metrics = None
    return client


def _tables(client: MagicMock) -> list[str]:
    """The tables a mock client was asked to read, in call order."""
    return [call.args[0] for call in client.sync_get_item.call_args_list]


def test_the_child_uses_its_own_client_after_the_parent_resolved():
    """Parent first, child second: the child still reads through its client."""
    parent_client, child_client = _client(), _client()

    class Parent(Model):
        model_config = ModelConfig(table="parents", client=parent_client)
        pk = StringAttribute(partition_key=True)

    class Child(Parent):
        model_config = ModelConfig(table="children", client=child_client)

    Parent.sync_get(pk="one")
    Child.sync_get(pk="two")

    assert _tables(parent_client) == ["parents"]
    assert _tables(child_client) == ["children"]


def test_the_parent_keeps_its_client_after_the_child_resolved():
    """Child first, parent second: resolving the child leaves the parent alone."""
    parent_client, child_client = _client(), _client()

    class Parent(Model):
        model_config = ModelConfig(table="parents", client=parent_client)
        pk = StringAttribute(partition_key=True)

    class Child(Parent):
        model_config = ModelConfig(table="children", client=child_client)

    Child.sync_get(pk="two")
    Parent.sync_get(pk="one")

    assert _tables(child_client) == ["children"]
    assert _tables(parent_client) == ["parents"]


def test_siblings_keep_their_own_clients():
    """Two children of one parent do not share the first client that resolved."""
    parent_client = _client()
    left_client, right_client = _client(), _client()

    class Parent(Model):
        model_config = ModelConfig(table="parents", client=parent_client)
        pk = StringAttribute(partition_key=True)

    class Left(Parent):
        model_config = ModelConfig(table="left", client=left_client)

    class Right(Parent):
        model_config = ModelConfig(table="right", client=right_client)

    Parent.sync_get(pk="one")
    Left.sync_get(pk="left")
    Right.sync_get(pk="right")

    assert _tables(parent_client) == ["parents"]
    assert _tables(left_client) == ["left"]
    assert _tables(right_client) == ["right"]


def test_a_grandchild_keeps_its_own_client():
    """Deeper inheritance does not reach past the nearest configured client."""
    parent_client, child_client, grandchild_client = _client(), _client(), _client()

    class Parent(Model):
        model_config = ModelConfig(table="parents", client=parent_client)
        pk = StringAttribute(partition_key=True)

    class Child(Parent):
        model_config = ModelConfig(table="children", client=child_client)

    class Grandchild(Child):
        model_config = ModelConfig(table="grandchildren", client=grandchild_client)

    Parent.sync_get(pk="one")
    Child.sync_get(pk="child")
    Grandchild.sync_get(pk="grandchild")

    assert _tables(parent_client) == ["parents"]
    assert _tables(child_client) == ["children"]
    assert _tables(grandchild_client) == ["grandchildren"]


async def test_an_async_read_uses_the_child_client():
    """The async path resolves the same per-class client as the sync one."""
    parent_client, child_client = _client(), _client()

    class Parent(Model):
        model_config = ModelConfig(table="parents", client=parent_client)
        pk = StringAttribute(partition_key=True)

    class Child(Parent):
        model_config = ModelConfig(table="children", client=child_client)

    await Parent.get(pk="one")
    await Child.get(pk="two")

    assert [c.args[0] for c in parent_client.get_item.call_args_list] == ["parents"]
    assert [c.args[0] for c in child_client.get_item.call_args_list] == ["children"]


def test_a_child_without_its_own_config_uses_the_parent_client():
    """A child that inherits the configuration inherits the client it names."""
    parent_client = _client()

    class Parent(Model):
        model_config = ModelConfig(table="parents", client=parent_client)
        pk = StringAttribute(partition_key=True)

    class Child(Parent):
        pass

    Parent.sync_get(pk="one")
    Child.sync_get(pk="two")

    assert _tables(parent_client) == ["parents", "parents"]
    assert Child._get_client() is parent_client


def test_a_child_without_a_client_falls_back_to_the_default_not_the_parent():
    """An explicit parent client is not inherited when the child names none."""
    parent_client, default_client = _client(), _client()

    class Parent(Model):
        model_config = ModelConfig(table="parents", client=parent_client)
        pk = StringAttribute(partition_key=True)

    class Child(Parent):
        model_config = ModelConfig(table="children")

    set_default_client(default_client)
    try:
        Parent.sync_get(pk="one")
        Child.sync_get(pk="two")
    finally:
        clear_default_client()

    assert _tables(parent_client) == ["parents"]
    assert _tables(default_client) == ["children"]


@pytest.fixture(autouse=True)
def _clean_default_client():
    """Leave no default client behind for the tests that do not set one."""
    yield
    clear_default_client()
