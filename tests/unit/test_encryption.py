"""Tests for encryption module."""

from unittest.mock import MagicMock, patch

import pytest
from pydynox._internal._encryption import EncryptionMode, KmsEncryptor
from pydynox.attributes import EncryptedAttribute

# --- EncryptionMode ---


def test_encryption_mode_values():
    """EncryptionMode has correct values."""
    # THEN each mode should have the expected value
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
    # WHEN we check if value is encrypted
    result = KmsEncryptor.is_encrypted(value)

    # THEN it should match expected
    assert result == expected


# --- EncryptedAttribute ---


def test_encrypted_attribute_type():
    """EncryptedAttribute has string type."""
    # GIVEN an encrypted attribute
    attr = EncryptedAttribute(key_id="alias/test")

    # THEN attr_type should be string
    assert attr.attr_type == "S"


def test_encrypted_attribute_stores_config():
    """EncryptedAttribute stores key_id, mode, region, context."""
    # WHEN we create an encrypted attribute with all options
    attr = EncryptedAttribute(
        key_id="alias/test",
        mode=EncryptionMode.WriteOnly,
        region="us-west-2",
        context={"tenant": "abc"},
    )

    # THEN all config should be stored
    assert attr.key_id == "alias/test"
    assert attr.mode == EncryptionMode.WriteOnly
    assert attr.region == "us-west-2"
    assert attr.context == {"tenant": "abc"}


def test_encrypted_attribute_default_mode():
    """Default mode is None (means ReadWrite)."""
    # WHEN we create an encrypted attribute without mode
    attr = EncryptedAttribute(key_id="alias/test")

    # THEN mode should be None (defaults to ReadWrite)
    assert attr.mode is None


def test_encrypted_attribute_no_key_flags():
    """EncryptedAttribute cannot be partition_key or sort_key."""
    # GIVEN an encrypted attribute
    attr = EncryptedAttribute(key_id="alias/test")

    # THEN it should not be a key
    assert attr.partition_key is False
    assert attr.sort_key is False


def test_encrypted_attribute_none_value():
    """None values are handled correctly."""
    # GIVEN an encrypted attribute
    attr = EncryptedAttribute(key_id="alias/test")

    # WHEN we serialize/deserialize None
    # THEN None should be returned
    assert attr.serialize(None) is None
    assert attr.deserialize(None) is None


@patch("pydynox.attributes.encrypted.KmsEncryptor")
def test_encrypted_attribute_serialize_calls_encrypt(mock_kms_class):
    """serialize calls encryptor.sync_encrypt_with_metrics."""
    # GIVEN a mocked encryptor
    mock_encryptor = MagicMock()
    mock_result = MagicMock()
    mock_result.ciphertext = "ENC:encrypted_data"
    mock_result.metrics.duration_ms = 10.0
    mock_result.metrics.kms_calls = 1
    mock_encryptor.sync_encrypt_with_metrics.return_value = mock_result
    mock_kms_class.return_value = mock_encryptor

    attr = EncryptedAttribute(key_id="alias/test")

    # WHEN we serialize a value
    result = attr.serialize("secret")

    # THEN sync_encrypt_with_metrics should be called
    mock_encryptor.sync_encrypt_with_metrics.assert_called_once_with("secret")
    assert result == "ENC:encrypted_data"


@patch("pydynox.attributes.encrypted.KmsEncryptor")
def test_encrypted_attribute_deserialize_calls_decrypt(mock_kms_class):
    """deserialize calls encryptor.sync_decrypt_with_metrics for encrypted values."""
    # GIVEN a mocked encryptor
    mock_encryptor = MagicMock()
    mock_result = MagicMock()
    mock_result.plaintext = "secret"
    mock_result.metrics.duration_ms = 10.0
    mock_result.metrics.kms_calls = 1
    mock_encryptor.sync_decrypt_with_metrics.return_value = mock_result
    mock_kms_class.return_value = mock_encryptor
    mock_kms_class.is_encrypted.return_value = True

    attr = EncryptedAttribute(key_id="alias/test")

    # WHEN we deserialize an encrypted value
    result = attr.deserialize("ENC:encrypted_data")

    # THEN sync_decrypt_with_metrics should be called
    mock_encryptor.sync_decrypt_with_metrics.assert_called_once_with("ENC:encrypted_data")
    assert result == "secret"


def test_encrypted_attribute_deserialize_plain_value():
    """deserialize returns plain values unchanged."""
    # GIVEN an encrypted attribute
    attr = EncryptedAttribute(key_id="alias/test")

    # WHEN we deserialize a plain value
    result = attr.deserialize("plain text")

    # THEN it should be returned unchanged
    assert result == "plain text"


@patch("pydynox.attributes.encrypted.KmsEncryptor")
def test_encrypted_attribute_lazy_loads_encryptor(mock_kms_class):
    """Encryptor is created on first use, not on init."""
    # GIVEN an encrypted attribute
    attr = EncryptedAttribute(
        key_id="alias/test",
        mode=EncryptionMode.WriteOnly,
        region="us-west-2",
        context={"tenant": "abc"},
    )

    # THEN encryptor should not be created yet
    mock_kms_class.assert_not_called()

    # WHEN we access the encryptor
    _ = attr.encryptor

    # THEN it should be created with correct args
    mock_kms_class.assert_called_once_with(
        key_id="alias/test",
        region="us-west-2",
        context={"tenant": "abc"},
    )


# --- Mode checks in Python ---


def test_encrypted_attribute_readonly_skips_encrypt():
    """ReadOnly mode returns value as-is on serialize."""
    # GIVEN an attribute with ReadOnly mode
    attr = EncryptedAttribute(key_id="alias/test", mode=EncryptionMode.ReadOnly)

    # WHEN we serialize
    result = attr.serialize("secret")

    # THEN value should be returned without encrypting
    assert result == "secret"


@patch("pydynox.attributes.encrypted.KmsEncryptor")
def test_encrypted_attribute_writeonly_skips_decrypt(mock_kms_class):
    """WriteOnly mode returns encrypted value as-is on deserialize."""
    # GIVEN an attribute with WriteOnly mode
    mock_kms_class.is_encrypted.return_value = True

    attr = EncryptedAttribute(key_id="alias/test", mode=EncryptionMode.WriteOnly)

    # WHEN we deserialize an encrypted value
    result = attr.deserialize("ENC:encrypted_data")

    # THEN encrypted value should be returned without decrypting
    assert result == "ENC:encrypted_data"


@patch("pydynox.attributes.encrypted.KmsEncryptor")
def test_encrypted_attribute_readwrite_can_do_both(mock_kms_class):
    """ReadWrite mode allows both encrypt and decrypt."""
    # GIVEN a mocked encryptor with ReadWrite mode
    mock_encryptor = MagicMock()
    mock_encrypt_result = MagicMock()
    mock_encrypt_result.ciphertext = "ENC:data"
    mock_encrypt_result.metrics.duration_ms = 10.0
    mock_encrypt_result.metrics.kms_calls = 1
    mock_encryptor.sync_encrypt_with_metrics.return_value = mock_encrypt_result

    mock_decrypt_result = MagicMock()
    mock_decrypt_result.plaintext = "secret"
    mock_decrypt_result.metrics.duration_ms = 10.0
    mock_decrypt_result.metrics.kms_calls = 1
    mock_encryptor.sync_decrypt_with_metrics.return_value = mock_decrypt_result

    mock_kms_class.return_value = mock_encryptor
    mock_kms_class.is_encrypted.return_value = True

    attr = EncryptedAttribute(key_id="alias/test", mode=EncryptionMode.ReadWrite)

    # WHEN we serialize and deserialize
    # THEN both should work
    assert attr.serialize("secret") == "ENC:data"
    assert attr.deserialize("ENC:data") == "secret"


# --- Additional coverage tests ---


def test_encrypted_attribute_deserialize_non_string():
    """deserialize converts non-string values to string."""
    # GIVEN an encrypted attribute
    attr = EncryptedAttribute(key_id="alias/test")

    # WHEN we deserialize a non-string value
    result = attr.deserialize(12345)

    # THEN it should be converted to string
    assert result == "12345"


def test_encrypted_attribute_can_encrypt_default_mode():
    """_can_encrypt returns True when mode is None (default)."""
    # GIVEN an attribute with default mode (None)
    attr = EncryptedAttribute(key_id="alias/test")

    # THEN _can_encrypt should return True
    assert attr._can_encrypt() is True


def test_encrypted_attribute_can_decrypt_default_mode():
    """_can_decrypt returns True when mode is None (default)."""
    # GIVEN an attribute with default mode (None)
    attr = EncryptedAttribute(key_id="alias/test")

    # THEN _can_decrypt should return True
    assert attr._can_decrypt() is True


def test_encrypted_attribute_can_encrypt_readwrite():
    """_can_encrypt returns True for ReadWrite mode."""
    # GIVEN an attribute with ReadWrite mode
    attr = EncryptedAttribute(key_id="alias/test", mode=EncryptionMode.ReadWrite)

    # THEN _can_encrypt should return True
    assert attr._can_encrypt() is True


def test_encrypted_attribute_can_decrypt_readwrite():
    """_can_decrypt returns True for ReadWrite mode."""
    # GIVEN an attribute with ReadWrite mode
    attr = EncryptedAttribute(key_id="alias/test", mode=EncryptionMode.ReadWrite)

    # THEN _can_decrypt should return True
    assert attr._can_decrypt() is True


def test_encrypted_attribute_can_encrypt_writeonly():
    """_can_encrypt returns True for WriteOnly mode."""
    # GIVEN an attribute with WriteOnly mode
    attr = EncryptedAttribute(key_id="alias/test", mode=EncryptionMode.WriteOnly)

    # THEN _can_encrypt should return True
    assert attr._can_encrypt() is True


def test_encrypted_attribute_cannot_decrypt_writeonly():
    """_can_decrypt returns False for WriteOnly mode."""
    # GIVEN an attribute with WriteOnly mode
    attr = EncryptedAttribute(key_id="alias/test", mode=EncryptionMode.WriteOnly)

    # THEN _can_decrypt should return False
    assert attr._can_decrypt() is False


def test_encrypted_attribute_cannot_encrypt_readonly():
    """_can_encrypt returns False for ReadOnly mode."""
    # GIVEN an attribute with ReadOnly mode
    attr = EncryptedAttribute(key_id="alias/test", mode=EncryptionMode.ReadOnly)

    # THEN _can_encrypt should return False
    assert attr._can_encrypt() is False


def test_encrypted_attribute_can_decrypt_readonly():
    """_can_decrypt returns True for ReadOnly mode."""
    # GIVEN an attribute with ReadOnly mode
    attr = EncryptedAttribute(key_id="alias/test", mode=EncryptionMode.ReadOnly)

    # THEN _can_decrypt should return True
    assert attr._can_decrypt() is True


@patch("pydynox.attributes.encrypted.KmsEncryptor")
def test_encrypted_attribute_encryptor_lazy_load_creates_once(mock_kms_class):
    """Encryptor is created once and reused."""
    # GIVEN an encrypted attribute
    mock_encryptor = MagicMock()
    mock_kms_class.return_value = mock_encryptor

    attr = EncryptedAttribute(key_id="alias/test")

    # WHEN we access encryptor multiple times
    enc1 = attr.encryptor
    enc2 = attr.encryptor

    # THEN it should be created only once
    mock_kms_class.assert_called_once()
    assert enc1 is enc2
