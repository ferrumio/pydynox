from pydynox import Model, ModelConfig
from pydynox.attributes import BooleanAttribute, StringAttribute


class User(Model):
    model_config = ModelConfig(table="users")

    pk = StringAttribute(partition_key=True)
    recommendations_enabled = BooleanAttribute(
        default=False,  # Used when loading existing items without the field
        default_for_new=True,  # Used when creating a new User without the field
    )


new_user = User(pk="USER#new")
assert new_user.recommendations_enabled is True

existing_user = User.from_dict({"pk": "USER#existing"})
assert existing_user.recommendations_enabled is False
