"""How to handle None values in type checking."""

from pydynox import Model, ModelConfig
from pydynox.attributes import StringAttribute


class User(Model):
    model_config = ModelConfig(table="users")

    pk = StringAttribute(partition_key=True)
    name = StringAttribute()


# All attributes can be None, so you need to handle it


def get_name_with_default(user: User) -> str:
    """Return name or empty string if None."""
    return user.name or ""


def get_name_with_check(user: User) -> str:
    """Raise if name is None."""
    if user.name is None:
        raise ValueError("User has no name")
    return user.name


def get_name_safe(user: User) -> str | None:
    """Return name as-is (may be None)."""
    return user.name
