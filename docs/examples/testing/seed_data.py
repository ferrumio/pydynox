"""Using seed data with pydynox_memory_backend_factory."""

import pytest
from pydynox import Model, ModelConfig
from pydynox.attributes import NumberAttribute, StringAttribute


class User(Model):
    model_config = ModelConfig(table="users")
    pk = StringAttribute(hash_key=True)
    name = StringAttribute()
    age = NumberAttribute(default=0)


class Order(Model):
    model_config = ModelConfig(table="orders")
    pk = StringAttribute(hash_key=True)
    sk = StringAttribute(range_key=True)
    total = NumberAttribute()


def test_with_seed_data(pydynox_memory_backend_factory):
    """Test with pre-populated data."""
    seed = {
        "users": [
            {"pk": "USER#1", "name": "Alice", "age": 30},
            {"pk": "USER#2", "name": "Bob", "age": 25},
        ]
    }

    with pydynox_memory_backend_factory(seed=seed):
        # Data is already there!
        alice = User.get(pk="USER#1")
        assert alice.name == "Alice"

        bob = User.get(pk="USER#2")
        assert bob.name == "Bob"


def test_with_multiple_tables(pydynox_memory_backend_factory):
    """Seed multiple tables at once."""
    seed = {
        "users": [{"pk": "USER#1", "name": "John", "age": 30}],
        "orders": [
            {"pk": "USER#1", "sk": "ORDER#001", "total": 100},
            {"pk": "USER#1", "sk": "ORDER#002", "total": 200},
        ],
    }

    with pydynox_memory_backend_factory(seed=seed):
        user = User.get(pk="USER#1")
        assert user is not None

        orders = list(Order.query(hash_key="USER#1"))
        assert len(orders) == 2


# Alternative: use pydynox_seed fixture in conftest.py
@pytest.fixture
def pydynox_seed():
    """Override this in conftest.py to provide default seed data."""
    return {
        "users": [
            {"pk": "ADMIN#1", "name": "Admin", "age": 99},
        ]
    }


def test_with_seeded_fixture(pydynox_memory_backend_seeded):
    """Uses seed data from pydynox_seed fixture."""
    admin = User.get(pk="ADMIN#1")
    assert admin.name == "Admin"
