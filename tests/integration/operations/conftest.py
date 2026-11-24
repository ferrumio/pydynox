"""Model fixtures shared by sync and async projection tests."""

import pytest
from pydynox import Model, ModelConfig
from pydynox.attributes import (
    ListAttribute,
    MapAttribute,
    NumberAttribute,
    StringAttribute,
    StringSetAttribute,
)


@pytest.fixture
def user_cls(dynamo):
    class User(Model):
        model_config = ModelConfig(table="test_table", client=dynamo)
        pk = StringAttribute(partition_key=True)
        sk = StringAttribute(sort_key=True)
        name = StringAttribute(required=True)
        age = NumberAttribute(default=0)
        email = StringAttribute()

    return User


@pytest.fixture
def account_cls(dynamo):
    class Account(Model):
        model_config = ModelConfig(table="test_table", client=dynamo)
        pk = StringAttribute(partition_key=True)
        sk = StringAttribute(sort_key=True)
        tags = ListAttribute()
        prefs = MapAttribute()
        labels = StringSetAttribute()
        details = MapAttribute()
        name = StringAttribute()

    return Account
