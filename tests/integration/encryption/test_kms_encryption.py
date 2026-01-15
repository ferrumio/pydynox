"""Integration tests for KMS envelope encryption.

Tests the full encrypt/decrypt cycle using LocalStack KMS.
"""

import pytest
from pydynox._internal._encryption import KmsEncryptor

# --- Basic encrypt/decrypt ---


def test_encrypt_decrypt_roundtrip(localstack_endpoint, kms_key_id):
    """Encrypt then decrypt returns original value."""
    # GIVEN a KMS encryptor
    encryptor = KmsEncryptor(
        key_id=kms_key_id,
        endpoint_url=localstack_endpoint,
        access_key="testing",
        secret_key="testing",
        region="us-east-1",
    )

    # WHEN we encrypt and decrypt
    plaintext = "my secret data"
    encrypted = encryptor.encrypt(plaintext)
    decrypted = encryptor.decrypt(encrypted)

    # THEN we get the original value back
    assert decrypted == plaintext
    assert encrypted.startswith("ENC:")
    assert encrypted != plaintext


def test_encrypt_produces_different_ciphertext(localstack_endpoint, kms_key_id):
    """Each encrypt call produces different ciphertext (random nonce)."""
    # GIVEN a KMS encryptor
    encryptor = KmsEncryptor(
        key_id=kms_key_id,
        endpoint_url=localstack_endpoint,
        access_key="testing",
        secret_key="testing",
        region="us-east-1",
    )

    # WHEN we encrypt the same data twice
    plaintext = "same data"
    encrypted1 = encryptor.encrypt(plaintext)
    encrypted2 = encryptor.encrypt(plaintext)

    # THEN ciphertext is different (random nonce)
    assert encrypted1 != encrypted2

    # AND both decrypt to the same value
    assert encryptor.decrypt(encrypted1) == plaintext
    assert encryptor.decrypt(encrypted2) == plaintext


# --- Large data (tests no 4KB limit) ---


def test_encrypt_large_data(localstack_endpoint, kms_key_id):
    """Encrypt data larger than KMS 4KB limit."""
    # GIVEN a KMS encryptor
    encryptor = KmsEncryptor(
        key_id=kms_key_id,
        endpoint_url=localstack_endpoint,
        access_key="testing",
        secret_key="testing",
        region="us-east-1",
    )

    # WHEN we encrypt 100KB of data (way over KMS 4KB limit)
    plaintext = "x" * 100_000
    encrypted = encryptor.encrypt(plaintext)
    decrypted = encryptor.decrypt(encrypted)

    # THEN it works (envelope encryption handles large data)
    assert decrypted == plaintext
    assert len(plaintext) == 100_000


def test_encrypt_unicode(localstack_endpoint, kms_key_id):
    """Encrypt unicode data."""
    encryptor = KmsEncryptor(
        key_id=kms_key_id,
        endpoint_url=localstack_endpoint,
        access_key="testing",
        secret_key="testing",
        region="us-east-1",
    )

    plaintext = "Hello 世界 🔐 émojis"
    encrypted = encryptor.encrypt(plaintext)
    decrypted = encryptor.decrypt(encrypted)

    assert decrypted == plaintext


# --- Encryption context ---


def test_encryption_context(localstack_endpoint, kms_key_id):
    """Encryption context must match on decrypt."""
    context = {"tenant": "acme", "purpose": "test"}

    encryptor = KmsEncryptor(
        key_id=kms_key_id,
        endpoint_url=localstack_endpoint,
        access_key="testing",
        secret_key="testing",
        region="us-east-1",
        context=context,
    )

    plaintext = "secret with context"
    encrypted = encryptor.encrypt(plaintext)
    decrypted = encryptor.decrypt(encrypted)

    assert decrypted == plaintext


def test_wrong_context_fails(localstack_endpoint, kms_key_id):
    """Decrypt with wrong context fails."""
    # GIVEN two encryptors with different contexts
    encryptor1 = KmsEncryptor(
        key_id=kms_key_id,
        endpoint_url=localstack_endpoint,
        access_key="testing",
        secret_key="testing",
        region="us-east-1",
        context={"tenant": "acme"},
    )

    encryptor2 = KmsEncryptor(
        key_id=kms_key_id,
        endpoint_url=localstack_endpoint,
        access_key="testing",
        secret_key="testing",
        region="us-east-1",
        context={"tenant": "other"},
    )

    # WHEN we encrypt with one context
    encrypted = encryptor1.encrypt("secret")

    # THEN decrypting with different context fails
    from pydynox.exceptions import EncryptionError

    with pytest.raises(EncryptionError):
        encryptor2.decrypt(encrypted)


# --- is_encrypted helper ---


@pytest.mark.parametrize(
    "value,expected",
    [
        pytest.param("ENC:abc123", True, id="encrypted"),
        pytest.param("plain text", False, id="plain"),
        pytest.param("", False, id="empty"),
        pytest.param("ENC:", True, id="prefix_only"),
    ],
)
def test_is_encrypted(value, expected):
    """is_encrypted detects ENC: prefix."""
    assert KmsEncryptor.is_encrypted(value) == expected


# --- Error cases ---


def test_decrypt_invalid_prefix(localstack_endpoint, kms_key_id):
    """Decrypt without ENC: prefix fails."""
    encryptor = KmsEncryptor(
        key_id=kms_key_id,
        endpoint_url=localstack_endpoint,
        access_key="testing",
        secret_key="testing",
        region="us-east-1",
    )

    with pytest.raises(ValueError, match="must start with 'ENC:'"):
        encryptor.decrypt("not encrypted")


def test_decrypt_invalid_base64(localstack_endpoint, kms_key_id):
    """Decrypt with invalid base64 fails."""
    encryptor = KmsEncryptor(
        key_id=kms_key_id,
        endpoint_url=localstack_endpoint,
        access_key="testing",
        secret_key="testing",
        region="us-east-1",
    )

    with pytest.raises(ValueError, match="Invalid base64"):
        encryptor.decrypt("ENC:not-valid-base64!!!")


def test_invalid_key_id(localstack_endpoint):
    """Invalid KMS key ID fails on encrypt."""
    # GIVEN an encryptor with invalid key ID
    encryptor = KmsEncryptor(
        key_id="invalid-key-id",
        endpoint_url=localstack_endpoint,
        access_key="testing",
        secret_key="testing",
        region="us-east-1",
    )

    # WHEN we try to encrypt
    # THEN EncryptionError is raised
    from pydynox.exceptions import EncryptionError

    with pytest.raises(EncryptionError):
        encryptor.encrypt("test")
