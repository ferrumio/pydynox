"""Encryption modes example."""

from pydynox import Model, ModelConfig
from pydynox.attributes import EncryptedAttribute, EncryptionMode, StringAttribute


# Write-only service: can encrypt, cannot decrypt
class IngestService(Model):
    model_config = ModelConfig(table="users")

    pk = StringAttribute(partition_key=True)
    ssn = EncryptedAttribute(
        key_id="alias/my-app-key",
        mode=EncryptionMode.WriteOnly,
    )


# Read-only service: can decrypt, cannot encrypt
class ReportService(Model):
    model_config = ModelConfig(table="users")

    pk = StringAttribute(partition_key=True)
    ssn = EncryptedAttribute(
        key_id="alias/my-app-key",
        mode=EncryptionMode.ReadOnly,
    )


# Full access (default): can encrypt and decrypt
class AdminService(Model):
    model_config = ModelConfig(table="users")

    pk = StringAttribute(partition_key=True)
    ssn = EncryptedAttribute(key_id="alias/my-app-key")
