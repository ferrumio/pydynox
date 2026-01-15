"""Tests for encryption module."""

from unittest.mock import MagicMock, patch

import pytest
from pydynox._internal._encryption import EncryptionMode, KmsEncryptor
from pydynox.attributes import EncryptedAttribute

# --- EncryptionMode ---


def test_encryption_mode_values():
    """EncryptionMode has correct values."""
    assert EncryptionMode.ReadWrite == 0
    assert EncryptionMode.WriteOnly == 1
    assert EncryptionMode.ReadOnly == 2


# --- KmsEncryptor.is_encrypted ---


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


# --- EncryptedAttribute ---


def test_encrypted_attribute_type():
    """EncryptedAttribute has string type."""
    attr = EncryptedAttribute(key_id="alias/test")

    assert attr.attr_type == "S"


def test_encrypted_attribute_stores_config():
    """EncryptedAttribute stores key_id, mode, region, context."""
    attr = EncryptedAttribute(
        key_id="alias/test",
        mode=EncryptionMode.WriteOnly,
        region="us-west-2",
        context={"tenant": "abc"},
    )

    assert attr.key_id == "alias/test"
    assert attr.mode == EncryptionMode.WriteOnly
    assert attr.region == "us-west-2"
    assert attr.context == {"tenant": "abc"}


def test_encrypted_attribute_default_mode():
    """Default mode is None (means ReadWrite)."""
    attr = EncryptedAttribute(key_id="alias/test")

    assert attr.mode is None


def test_encrypted_attribute_no_key_flags():
    """EncryptedAttribute cannot be hash_key or range_key."""
    attr = EncryptedAttribute(key_id="alias/test")

    assert attr.hash_key is False
    assert attr.range_key is False


def test_encrypted_attribute_none_value():
    """None values are handled correctly."""
    attr = EncryptedAttribute(key_id="alias/test")

    assert attr.serialize(None) is None
    assert attr.deserialize(None) is None


@patch("pydynox.attributes.encrypted.KmsEncryptor")
def test_encrypted_attribute_serialize_calls_encrypt(mock_kms_class):
    """serialize calls encryptor.encrypt_with_metrics."""
    mock_encryptor = MagicMock()
    mock_result = MagicMock()
    mock_result.ciphertext = "ENC:encrypted_data"
    mock_result.metrics.duration_ms = 10.0
    mock_result.metrics.kms_calls = 1
    mock_encryptor.encrypt_with_metrics.return_value = mock_result
    mock_kms_class.return_value = mock_encryptor

    attr = EncryptedAttribute(key_id="alias/test")
    result = attr.serialize("secret")

    mock_encryptor.encrypt_with_metrics.assert_called_once_with("secret")
    assert result == "ENC:encrypted_data"


@patch("pydynox.attributes.encrypted.KmsEncryptor")
def test_encrypted_attribute_deserialize_calls_decrypt(mock_kms_class):
    """deserialize calls encryptor.decrypt_with_metrics for encrypted values."""
    mock_encryptor = MagicMock()
    mock_result = MagicMock()
    mock_result.plaintext = "secret"
    mock_result.metrics.duration_ms = 10.0
    mock_result.metrics.kms_calls = 1
    mock_encryptor.decrypt_with_metrics.return_value = mock_result
    mock_kms_class.return_value = mock_encryptor
    mock_kms_class.is_encrypted.return_value = True

    attr = EncryptedAttribute(key_id="alias/test")
    result = attr.deserialize("ENC:encrypted_data")

    mock_encryptor.decrypt_with_metrics.assert_called_once_with("ENC:encrypted_data")
    assert result == "secret"


def test_encrypted_attribute_deserialize_plain_value():
    """deserialize returns plain values unchanged."""
    attr = EncryptedAttribute(key_id="alias/test")

    result = attr.deserialize("plain text")

    assert result == "plain text"


@patch("pydynox.attributes.encrypted.KmsEncryptor")
def test_encrypted_attribute_lazy_loads_encryptor(mock_kms_class):
    """Encryptor is created on first use, not on init."""
    attr = EncryptedAttribute(
        key_id="alias/test",
        mode=EncryptionMode.WriteOnly,
        region="us-west-2",
        context={"tenant": "abc"},
    )

    # Not created yet
    mock_kms_class.assert_not_called()

    # Access encryptor
    _ = attr.encryptor

    # Now created with correct args (no mode - it's handled in Python)
    mock_kms_class.assert_called_once_with(
        key_id="alias/test",
        region="us-west-2",
        context={"tenant": "abc"},
    )


# --- Mode checks in Python ---


def test_encrypted_attribute_readonly_skips_encrypt():
    """ReadOnly mode returns value as-is on serialize."""
    attr = EncryptedAttribute(key_id="alias/test", mode=EncryptionMode.ReadOnly)

    result = attr.serialize("secret")

    # Should return the value without encrypting
    assert result == "secret"


@patch("pydynox.attributes.encrypted.KmsEncryptor")
def test_encrypted_attribute_writeonly_skips_decrypt(mock_kms_class):
    """WriteOnly mode returns encrypted value as-is on deserialize."""
    mock_kms_class.is_encrypted.return_value = True

    attr = EncryptedAttribute(key_id="alias/test", mode=EncryptionMode.WriteOnly)

    result = attr.deserialize("ENC:encrypted_data")

    # Should return the encrypted value without decrypting
    assert result == "ENC:encrypted_data"


@patch("pydynox.attributes.encrypted.KmsEncryptor")
def test_encrypted_attribute_readwrite_can_do_both(mock_kms_class):
    """ReadWrite mode allows both encrypt and decrypt."""
    mock_encryptor = MagicMock()
    mock_encrypt_result = MagicMock()
    mock_encrypt_result.ciphertext = "ENC:data"
    mock_encrypt_result.metrics.duration_ms = 10.0
    mock_encrypt_result.metrics.kms_calls = 1
    mock_encryptor.encrypt_with_metrics.return_value = mock_encrypt_result

    mock_decrypt_result = MagicMock()
    mock_decrypt_result.plaintext = "secret"
    mock_decrypt_result.metrics.duration_ms = 10.0
    mock_decrypt_result.metrics.kms_calls = 1
    mock_encryptor.decrypt_with_metrics.return_value = mock_decrypt_result

    mock_kms_class.return_value = mock_encryptor
    mock_kms_class.is_encrypted.return_value = True

    attr = EncryptedAttribute(key_id="alias/test", mode=EncryptionMode.ReadWrite)

    # Both should work
    assert attr.serialize("secret") == "ENC:data"
    assert attr.deserialize("ENC:data") == "secret"
