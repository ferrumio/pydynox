"""Integration tests for EncryptionMode with Model.

Tests WriteOnly, ReadOnly, and ReadWrite modes in real scenarios.
"""

import uuid

import pytest
from pydynox import Model, ModelConfig, set_default_client
from pydynox._internal._encryption import EncryptionMode, KmsEncryptor
from pydynox.attributes import EncryptedAttribute, StringAttribute


@pytest.fixture
def writeonly_model(dynamo, localstack_endpoint, kms_key_id):
    """Create a model with WriteOnly encrypted attribute."""
    set_default_client(dynamo)

    table_name = "test_table"
    endpoint = localstack_endpoint
    key_id = kms_key_id

    class WriteOnlyModel(Model):
        model_config = ModelConfig(table=table_name)

        pk = StringAttribute(hash_key=True)
        sk = StringAttribute(range_key=True)
        secret = EncryptedAttribute(
            key_id=kms_key_id,
            region="us-east-1",
            mode=EncryptionMode.WriteOnly,
        )

    # Configure encryptor at class level
    WriteOnlyModel._attributes["secret"]._encryptor = KmsEncryptor(
        key_id=key_id,
        region="us-east-1",
        endpoint_url=endpoint,
        access_key="testing",
        secret_key="testing",
    )

    return WriteOnlyModel


@pytest.fixture
def readonly_model(dynamo, localstack_endpoint, kms_key_id):
    """Create a model with ReadOnly encrypted attribute."""
    set_default_client(dynamo)

    table_name = "test_table"
    endpoint = localstack_endpoint
    key_id = kms_key_id

    class ReadOnlyModel(Model):
        model_config = ModelConfig(table=table_name)

        pk = StringAttribute(hash_key=True)
        sk = StringAttribute(range_key=True)
        secret = EncryptedAttribute(
            key_id=kms_key_id,
            region="us-east-1",
            mode=EncryptionMode.ReadOnly,
        )

    # Configure encryptor at class level
    ReadOnlyModel._attributes["secret"]._encryptor = KmsEncryptor(
        key_id=key_id,
        region="us-east-1",
        endpoint_url=endpoint,
        access_key="testing",
        secret_key="testing",
    )

    return ReadOnlyModel


@pytest.fixture
def readwrite_model(dynamo, localstack_endpoint, kms_key_id):
    """Create a model with ReadWrite (default) encrypted attribute."""
    set_default_client(dynamo)

    table_name = "test_table"
    endpoint = localstack_endpoint
    key_id = kms_key_id

    class ReadWriteModel(Model):
        model_config = ModelConfig(table=table_name)

        pk = StringAttribute(hash_key=True)
        sk = StringAttribute(range_key=True)
        secret = EncryptedAttribute(
            key_id=kms_key_id,
            region="us-east-1",
            mode=EncryptionMode.ReadWrite,
        )

    # Configure encryptor at class level
    ReadWriteModel._attributes["secret"]._encryptor = KmsEncryptor(
        key_id=key_id,
        region="us-east-1",
        endpoint_url=endpoint,
        access_key="testing",
        secret_key="testing",
    )

    return ReadWriteModel


# --- WriteOnly mode ---


def test_writeonly_encrypts_on_save(writeonly_model, dynamo):
    """WriteOnly mode encrypts data on save."""
    item_id = str(uuid.uuid4())

    item = writeonly_model(
        pk=f"SECRET#{item_id}",
        sk="v1",
        secret="my-secret",
    )
    item.save()

    # Raw data should be encrypted
    raw = dynamo.get_item("test_table", {"pk": f"SECRET#{item_id}", "sk": "v1"})
    assert raw["secret"].startswith("ENC:")


def test_writeonly_returns_ciphertext_on_load(writeonly_model):
    """WriteOnly mode returns encrypted value on load (no decrypt)."""
    item_id = str(uuid.uuid4())

    item = writeonly_model(
        pk=f"SECRET#{item_id}",
        sk="v1",
        secret="my-secret",
    )
    item.save()

    # Load returns encrypted value
    loaded = writeonly_model.get(pk=f"SECRET#{item_id}", sk="v1")
    assert loaded.secret.startswith("ENC:")
    assert loaded.secret != "my-secret"


# --- ReadOnly mode ---


def test_readonly_stores_plaintext(readonly_model, dynamo):
    """ReadOnly mode stores value as-is (no encrypt)."""
    item_id = str(uuid.uuid4())

    item = readonly_model(
        pk=f"SECRET#{item_id}",
        sk="v1",
        secret="plaintext-value",
    )
    item.save()

    # Raw data should be plaintext
    raw = dynamo.get_item("test_table", {"pk": f"SECRET#{item_id}", "sk": "v1"})
    assert raw["secret"] == "plaintext-value"
    assert not raw["secret"].startswith("ENC:")


def test_readonly_decrypts_existing_data(readonly_model, readwrite_model):
    """ReadOnly mode can decrypt data encrypted by another service."""
    item_id = str(uuid.uuid4())

    # Write with full-access model
    writer = readwrite_model(
        pk=f"SECRET#{item_id}",
        sk="v1",
        secret="encrypted-by-writer",
    )
    writer.save()

    # Read with ReadOnly model
    loaded = readonly_model.get(pk=f"SECRET#{item_id}", sk="v1")
    assert loaded.secret == "encrypted-by-writer"


# --- ReadWrite mode ---


def test_readwrite_encrypts_and_decrypts(readwrite_model, dynamo):
    """ReadWrite mode encrypts on save and decrypts on load."""
    item_id = str(uuid.uuid4())

    item = readwrite_model(
        pk=f"SECRET#{item_id}",
        sk="v1",
        secret="full-access-secret",
    )
    item.save()

    # Raw data is encrypted
    raw = dynamo.get_item("test_table", {"pk": f"SECRET#{item_id}", "sk": "v1"})
    assert raw["secret"].startswith("ENC:")

    # Load decrypts
    loaded = readwrite_model.get(pk=f"SECRET#{item_id}", sk="v1")
    assert loaded.secret == "full-access-secret"


# --- Cross-mode workflows ---


def test_writeonly_and_readonly_workflow(writeonly_model, readonly_model):
    """WriteOnly writes, ReadOnly reads - typical ingest/report pattern."""
    item_id = str(uuid.uuid4())

    # Ingest service (WriteOnly) saves data
    ingest_item = writeonly_model(
        pk=f"SECRET#{item_id}",
        sk="v1",
        secret="sensitive-data-from-ingest",
    )
    ingest_item.save()

    # Report service (ReadOnly) reads data
    report_item = readonly_model.get(pk=f"SECRET#{item_id}", sk="v1")
    assert report_item.secret == "sensitive-data-from-ingest"


def test_readwrite_can_read_writeonly_data(readwrite_model, writeonly_model):
    """ReadWrite can read data written by WriteOnly."""
    item_id = str(uuid.uuid4())

    # WriteOnly saves
    writer = writeonly_model(
        pk=f"SECRET#{item_id}",
        sk="v1",
        secret="written-by-writeonly",
    )
    writer.save()

    # ReadWrite reads
    reader = readwrite_model.get(pk=f"SECRET#{item_id}", sk="v1")
    assert reader.secret == "written-by-writeonly"
