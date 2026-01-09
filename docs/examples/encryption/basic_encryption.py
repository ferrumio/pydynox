"""Basic field encryption example."""

from pydynox import Model, ModelConfig
from pydynox.attributes import EncryptedAttribute, StringAttribute


class User(Model):
    model_config = ModelConfig(table="users")

    pk = StringAttribute(hash_key=True)
    sk = StringAttribute(range_key=True)
    email = StringAttribute()
    ssn = EncryptedAttribute(key_id="alias/my-app-key")


# Create a user with sensitive data
user = User(
    pk="USER#ENC",
    sk="PROFILE",
    email="john@example.com",
    ssn="123-45-6789",
)
user.save()

# The SSN is encrypted in DynamoDB as "ENC:base64data..."
# When you read it back, it's decrypted automatically
loaded = User.get(pk="USER#ENC", sk="PROFILE")
print(loaded.ssn)  # "123-45-6789"
