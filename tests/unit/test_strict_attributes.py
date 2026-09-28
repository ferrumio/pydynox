"""Runtime validation of model field names."""

from decimal import Decimal

import pytest
from pydynox import Model, ModelConfig
from pydynox.attributes import DecimalAttribute, StringAttribute


class StrictUser(Model):
    model_config = ModelConfig(table="users", strict_attributes=True)
    pk = StringAttribute(partition_key=True)
    name = StringAttribute(alias="n")
    balance = DecimalAttribute(default=0)

    @property
    def display_name(self):
        return self.name

    @display_name.setter
    def display_name(self, value):
        self.name = value

    @property
    def label(self):
        return self.name


@pytest.mark.parametrize("name", ["naem", "n", "display_name", "_cache"])
def test_constructor_rejects_unknown_fields(name):
    # WHEN application input contains a name outside the declared fields
    # THEN it fails before any client is needed, naming the model and field
    with pytest.raises(AttributeError, match=f"StrictUser has no attribute '{name}'"):
        StrictUser(pk="USER#1", **{name: "Bob"})


@pytest.mark.parametrize("name", ["naem", "n", "label", "save", "model_config"])
def test_assignment_rejects_unknown_or_unwritable_names(name):
    # GIVEN a loaded model with no changes
    user = StrictUser.from_dict({"pk": "USER#1", "n": "Alice", "balance": 0})

    # WHEN assigning an unknown field, alias, method, or read-only property
    with pytest.raises(AttributeError, match=f"StrictUser has no attribute '{name}'"):
        setattr(user, name, "Bob")

    # THEN the failed assignment leaves the model unchanged
    assert user.name == "Alice"
    assert not user.is_dirty
    assert name not in user.__dict__


def test_valid_assignment_and_revert_keep_change_tracking():
    # GIVEN a loaded model using a DynamoDB alias
    user = StrictUser.from_dict({"pk": "USER#1", "n": "Alice", "balance": 0})

    # WHEN a declared field changes
    user.name = "Bob"

    # THEN it is tracked under its Python name and serialized under its alias
    assert user.changed_fields == ["name"]
    assert user.to_dict()["n"] == "Bob"

    # WHEN restoring the original value
    user.name = "Alice"

    # THEN there are no pending changes
    assert not user.is_dirty


def test_inherited_fields_properties_and_private_state():
    # GIVEN a subclass that inherits its configuration, fields, and property
    class Admin(StrictUser):
        role = StringAttribute(default="admin")

    user = Admin.from_dict({"pk": "USER#1", "n": "Alice", "balance": 0})

    # WHEN using a writable property, a subclass field, and temporary state
    user.display_name = "Bob"
    user.role = "owner"
    user._cache = {"request": "123"}

    # THEN only declared fields are tracked and serialized
    assert user.display_name == "Bob"
    assert user._cache == {"request": "123"}
    assert set(user.changed_fields) == {"name", "role"}
    assert user.to_dict() == {
        "pk": "USER#1",
        "n": "Bob",
        "balance": Decimal(0),
        "role": "owner",
    }
    with pytest.raises(AttributeError, match="Admin has no attribute 'naem'"):
        user.naem = "Charlie"


def test_strict_mode_keeps_field_value_validation():
    # GIVEN a strict model with a field that rejects floats
    user = StrictUser(pk="USER#1", balance=Decimal("1.25"))

    # WHEN invalid values are passed through either input path
    # THEN the existing field validation still runs
    with pytest.raises(TypeError):
        StrictUser(pk="USER#2", balance=1.25)
    with pytest.raises(TypeError):
        user.balance = 1.25
    assert user.balance == Decimal("1.25")


def test_strict_mode_keeps_required_fields():
    class RequiredUser(StrictUser):
        email = StringAttribute(required=True)

    with pytest.raises(ValueError, match="Attribute 'email' is required"):
        RequiredUser(pk="USER#1")


def test_strict_mode_keeps_template_keys_and_mixin_fields():
    # GIVEN fields inherited from a plain Python mixin and a generated key
    class AuditFields:
        created_by = StringAttribute()

    class User(Model, AuditFields):
        model_config = ModelConfig(table="users", strict_attributes=True)
        pk = StringAttribute(partition_key=True, template="USER#{email}")
        email = StringAttribute()

    # WHEN creating a model with declared input fields
    user = User(email="alice@example.com", created_by="admin")

    # THEN template generation and inherited fields still work
    assert user.pk == "USER#alice@example.com"
    user.created_by = "Alice"
    assert user.to_dict()["created_by"] == "Alice"


def test_subclass_can_disable_inherited_strict_mode():
    # GIVEN a subclass that opts out of its parent's strict mode
    class User(StrictUser):
        model_config = ModelConfig(table="users")

    # WHEN providing unknown names
    user = User(pk="USER#1", naem="Bob")
    user.request_id = "123"

    # THEN its own configuration takes precedence
    assert user.name is None
    assert user.request_id == "123"


def test_overridden_property_is_not_treated_as_writable():
    # GIVEN a subclass that replaces its parent's property with a constant
    class User(StrictUser):
        display_name = "Guest"

    user = User(pk="USER#1")

    # THEN the inherited setter must not allow an untracked assignment
    with pytest.raises(AttributeError, match="User has no attribute 'display_name'"):
        user.display_name = "Bob"


@pytest.mark.parametrize("strict", [False, True])
def test_from_dict_ignores_extra_stored_fields(strict):
    # GIVEN stored data that includes aliases and names reserved by the model
    class User(StrictUser):
        model_config = ModelConfig(table="users", strict_attributes=strict)

    data = {
        "pk": "USER#1",
        "n": "Alice",
        "balance": 0,
        "future_field": "value",
        "display_name": "Bob",
        "_cache": "stored value",
        "_original": "stored value",
    }

    # WHEN loading the item
    user = User.from_dict(data)

    # THEN extra data does not become application or internal state
    assert user.name == "Alice"
    assert user.display_name == "Alice"
    assert not hasattr(user, "future_field")
    assert not hasattr(user, "_cache")
    assert not user.is_dirty
    assert user.to_dict() == {"pk": "USER#1", "n": "Alice", "balance": Decimal(0)}
    assert data["n"] == "Alice"


@pytest.mark.parametrize("kind", [None, "FutureItem"])
def test_unknown_discriminator_still_loads_parent(kind):
    # GIVEN stored data with no known concrete model
    class Item(Model):
        model_config = ModelConfig(table="items", strict_attributes=True)
        pk = StringAttribute(partition_key=True)
        kind = StringAttribute(discriminator=True, alias="t")

    item = Item.from_dict({"pk": "ITEM#1", "t": kind, "future_field": "value"})

    # THEN strict validation does not reject the extra stored field
    assert type(item) is Item
    assert item.pk == "ITEM#1"
    assert not hasattr(item, "future_field")


@pytest.mark.parametrize("parent_strict,child_strict", [(True, True), (False, True), (True, False)])
def test_from_dict_uses_concrete_subclass_schema(parent_strict, child_strict):
    # GIVEN a discriminator alias and a field declared only by the child
    class Item(Model):
        model_config = ModelConfig(table="items", strict_attributes=parent_strict)
        pk = StringAttribute(partition_key=True)
        kind = StringAttribute(discriminator=True, alias="t")

    class Event(Item):
        model_config = ModelConfig(table="items", strict_attributes=child_strict)
        message = StringAttribute(alias="m")

    # WHEN loading through the parent
    event = Item.from_dict({"pk": "EVENT#1", "t": "Event", "m": "Hello", "future_field": "value"})

    # THEN the child field is loaded and extra stored fields are ignored
    assert isinstance(event, Event)
    assert event.message == "Hello"
    assert not hasattr(event, "future_field")
    assert not event.is_dirty
    if child_strict:
        with pytest.raises(AttributeError, match="Event has no attribute 'mesage'"):
            event.mesage = "Bye"
    else:
        event.mesage = "Bye"


@pytest.mark.parametrize("config", [None, ModelConfig(table="users")])
def test_default_behavior_still_allows_extra_names(config):
    # GIVEN a model without strict validation
    class User(Model):
        pk = StringAttribute(partition_key=True)
        name = StringAttribute()

    if config is not None:
        User.model_config = config

    # WHEN passing an unknown constructor argument or assigning temporary state
    user = User(pk="USER#1", naem="Bob")
    user.request_id = "123"

    # THEN the existing permissive behavior remains
    assert user.name is None
    assert not hasattr(user, "naem")
    assert user.request_id == "123"
    assert user.to_dict() == {"pk": "USER#1"}


def test_non_strict_custom_constructor_still_receives_extra_stored_fields():
    # GIVEN an existing model that handles extra data in its own constructor
    class User(Model):
        model_config = ModelConfig(table="users")
        pk = StringAttribute(partition_key=True)

        def __init__(self, request_id=None, **kwargs):
            super().__init__(**kwargs)
            self.request_id = request_id

    # WHEN loading stored data
    user = User.from_dict({"pk": "USER#1", "request_id": "123"})

    # THEN the new option does not change this existing extension point
    assert user.request_id == "123"
