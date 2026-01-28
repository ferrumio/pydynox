import asyncio

from pydynox import Model, ModelConfig
from pydynox.attributes import EncryptedAttribute, StringAttribute


class SecureUser(Model):
    model_config = ModelConfig(table="users")

    pk: str = StringAttribute(hash_key=True)
    sk: str = StringAttribute(range_key=True)
    ssn: str = EncryptedAttribute(key_id="alias/my-app-key")


async def main():
    # Save with encrypted field
    user = SecureUser(pk="USER#1", sk="PROFILE", ssn="123-45-6789")
    await user.save()

    # Check KMS metrics
    total = SecureUser.get_total_metrics()
    print(f"KMS duration: {total.kms_duration_ms}ms")
    print(f"KMS calls: {total.kms_calls}")


asyncio.run(main())
