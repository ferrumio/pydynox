"""Integration tests for EncryptedAttribute with Model.

Tests the real use case: saving and loading models with encrypted fields.
"""

import uuid

import pytest
from pydynox import Model, ModelConfig, set_default_client
from pydynox._internal._encryption import KmsEncryptor
from pydynox.attributes import EncryptedAttribute, StringAttribute


@pytest.fixture
def secret_model(dynamo, localstack_endpoint, kms_key_id):
    """Create a model with encrypted attribute."""
    set_default_client(dynamo)

    table_name = "test_table"
    endpoint = localstack_endpoint
    key_id = kms_key_id

    class SecretModel(Model):
        model_config = ModelConfig(table=table_name)

        pk = StringAttribute(hash_key=True)
        sk = StringAttribute(range_key=True)
        name = StringAttribute()
        secret = EncryptedAttribute(
            key_id=kms_key_id,
            region="us-east-1",
        )

    # Configure encryptor at class level
    SecretModel._attributes["secret"]._encryptor = KmsEncryptor(
        key_id=key_id,
        region="us-east-1",
        endpoint_url=endpoint,
        access_key="testing",
        secret_key="testing",
    )

    return SecretModel


@pytest.fixture
def secret_model_with_context(dynamo, localstack_endpoint, kms_key_id):
    """Create a model with encrypted attribute and context."""
    set_default_client(dynamo)

    table_name = "test_table"
    endpoint = localstack_endpoint
    key_id = kms_key_id
    context = {"tenant": "acme"}

    class SecretModelWithContext(Model):
        model_config = ModelConfig(table=table_name)

        pk = StringAttribute(hash_key=True)
        sk = StringAttribute(range_key=True)
        name = StringAttribute()
        secret = EncryptedAttribute(
            key_id=kms_key_id,
            region="us-east-1",
            context=context,
        )

    # Configure encryptor at class level
    SecretModelWithContext._attributes["secret"]._encryptor = KmsEncryptor(
        key_id=key_id,
        region="us-east-1",
        endpoint_url=endpoint,
        access_key="testing",
        secret_key="testing",
        context=context,
    )

    return SecretModelWithContext


def test_save_and_load_encrypted_field(secret_model):
    """Save model with encrypted field, load it back decrypted."""
    # GIVEN a model with secret data
    item_id = str(uuid.uuid4())
    secret_value = "my-super-secret-password"

    item = secret_model(
        pk=f"SECRET#{item_id}",
        sk="v1",
        name="test-secret",
        secret=secret_value,
    )

    # WHEN we save it
    item.save()

    # AND load it back
    loaded = secret_model.get(pk=f"SECRET#{item_id}", sk="v1")

    # THEN the secret is decrypted
    assert loaded.secret == secret_value
    assert loaded.name == "test-secret"


def test_encrypted_field_stored_as_ciphertext(secret_model, dynamo):
    """Verify the field is actually encrypted in DynamoDB."""
    # GIVEN a model with secret data
    item_id = str(uuid.uuid4())
    secret_value = "plaintext-secret"

    item = secret_model(
        pk=f"SECRET#{item_id}",
        sk="v1",
        name="test",
        secret=secret_value,
    )
    item.save()

    # WHEN we read raw data from DynamoDB
    raw = dynamo.get_item("test_table", {"pk": f"SECRET#{item_id}", "sk": "v1"})

    # THEN the secret is stored encrypted (starts with ENC:)
    assert raw["secret"].startswith("ENC:")
    assert raw["secret"] != secret_value


def test_encrypted_field_with_context(secret_model_with_context):
    """Encrypted field with context works."""
    # GIVEN a model with encryption context
    item_id = str(uuid.uuid4())
    secret_value = "secret-with-context"

    item = secret_model_with_context(
        pk=f"SECRET#{item_id}",
        sk="v1",
        name="test",
        secret=secret_value,
    )
    item.save()

    # WHEN we load it back
    loaded = secret_model_with_context.get(pk=f"SECRET#{item_id}", sk="v1")

    # THEN it decrypts correctly
    assert loaded.secret == secret_value


def test_encrypted_field_unicode(secret_model):
    """Encrypted field handles unicode."""
    # GIVEN unicode secret
    item_id = str(uuid.uuid4())
    secret_value = "密码 🔐 émojis"

    item = secret_model(
        pk=f"SECRET#{item_id}",
        sk="v1",
        name="unicode-test",
        secret=secret_value,
    )
    item.save()

    # WHEN we load it back
    loaded = secret_model.get(pk=f"SECRET#{item_id}", sk="v1")

    # THEN unicode is preserved
    assert loaded.secret == secret_value


def test_encrypted_field_large_value(secret_model):
    """Encrypted field handles large values (over KMS 4KB limit)."""
    # GIVEN a large secret (50KB)
    item_id = str(uuid.uuid4())
    secret_value = "x" * 50_000

    item = secret_model(
        pk=f"SECRET#{item_id}",
        sk="v1",
        name="large-secret",
        secret=secret_value,
    )
    item.save()

    # WHEN we load it back
    loaded = secret_model.get(pk=f"SECRET#{item_id}", sk="v1")

    # THEN it works (envelope encryption handles large data)
    assert loaded.secret == secret_value
    assert len(loaded.secret) == 50_000


def test_encrypted_field_null_value(secret_model):
    """Encrypted field handles null values."""
    # GIVEN a model without secret
    item_id = str(uuid.uuid4())

    item = secret_model(
        pk=f"SECRET#{item_id}",
        sk="v1",
        name="no-secret",
        secret=None,
    )
    item.save()

    # WHEN we load it back
    loaded = secret_model.get(pk=f"SECRET#{item_id}", sk="v1")

    # THEN secret is None
    assert loaded.secret is None


def test_encrypted_field_update(secret_model):
    """Encrypted field can be updated."""
    # GIVEN an existing item
    item_id = str(uuid.uuid4())

    item = secret_model(
        pk=f"SECRET#{item_id}",
        sk="v1",
        name="update-test",
        secret="original-secret",
    )
    item.save()

    # WHEN we update the secret
    item.secret = "new-secret"
    item.save()

    # AND load it back
    loaded = secret_model.get(pk=f"SECRET#{item_id}", sk="v1")

    # THEN the new secret is returned
    assert loaded.secret == "new-secret"
