from pydynox import Model, ModelConfig
from pydynox.attributes import NumberAttribute, StringAttribute
from pydynox.indexes import GlobalSecondaryIndex


class User(Model):
    model_config = ModelConfig(table="users")

    pk = StringAttribute(partition_key=True)
    sk = StringAttribute(sort_key=True)
    email = StringAttribute()
    status = StringAttribute()
    age = NumberAttribute()

    # GSI with hash key only
    email_index = GlobalSecondaryIndex(
        index_name="email-index",
        partition_key="email",
    )

    # GSI with hash and range key
    status_index = GlobalSecondaryIndex(
        index_name="status-index",
        partition_key="status",
        sort_key="pk",
    )
