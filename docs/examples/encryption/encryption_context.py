"""Encryption context example."""

from pydynox import Model, ModelConfig
from pydynox.attributes import EncryptedAttribute, StringAttribute


class User(Model):
    model_config = ModelConfig(table="users")

    pk = StringAttribute(hash_key=True)
    ssn = EncryptedAttribute(
        key_id="alias/my-app-key",
        context={"tenant": "acme-corp", "purpose": "pii"},
    )


# The context is passed to KMS on encrypt/decrypt.
# If the context doesn't match, decryption fails.
# This adds an extra layer of security.
