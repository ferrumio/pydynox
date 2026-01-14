from pydynox import Model, ModelConfig
from pydynox.attributes import StringAttribute


class User(Model):
    model_config = ModelConfig(table="users")

    pk = StringAttribute(hash_key=True)
    name = StringAttribute()
    status = StringAttribute()


# Scan with fields - useful for reports or exports
for user in User.scan(fields=["pk", "status"]):
    print(user.pk, user.status)
