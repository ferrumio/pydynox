"""Encrypted attribute type."""

from __future__ import annotations

from typing import Any

from pydynox._internal._encryption import EncryptionMode, KmsEncryptor
from pydynox._internal._operations_metrics import _record_kms_metrics
from pydynox.attributes.base import Attribute


class EncryptedAttribute(Attribute[str]):
    """Attribute that encrypts values using AWS KMS.

    Uses envelope encryption: GenerateDataKey + local AES-256-GCM.
    This removes the 4KB KMS limit and reduces API calls.

    Args:
        key_id: KMS key ID, ARN, or alias (e.g., "alias/my-key").
        mode: Controls what operations are allowed:
            - ReadWrite: Can encrypt and decrypt (default)
            - WriteOnly: Can only encrypt (fails on decrypt)
            - ReadOnly: Can only decrypt (fails on encrypt)
        region: AWS region (optional, uses default if not set).
        context: Encryption context dict for extra security (optional).

    Example:
        >>> from pydynox import Model, ModelConfig
        >>> from pydynox.attributes import StringAttribute, EncryptedAttribute, EncryptionMode
        >>>
        >>> class IngestService(Model):
        ...     model_config = ModelConfig(table="users")
        ...     pk = StringAttribute(hash_key=True)
        ...     # Write-only: can encrypt, fails on decrypt
        ...     ssn = EncryptedAttribute(
        ...         key_id="alias/my-key",
        ...         mode=EncryptionMode.WriteOnly,
        ...     )
        >>>
        >>> class ReportService(Model):
        ...     model_config = ModelConfig(table="users")
        ...     pk = StringAttribute(hash_key=True)
        ...     # Read-only: can decrypt, fails on encrypt
        ...     ssn = EncryptedAttribute(
        ...         key_id="alias/my-key",
        ...         mode=EncryptionMode.ReadOnly,
        ...     )
        >>>
        >>> class FullAccess(Model):
        ...     model_config = ModelConfig(table="users")
        ...     pk = StringAttribute(hash_key=True)
        ...     # Both (default)
        ...     ssn = EncryptedAttribute(key_id="alias/my-key")
    """

    attr_type = "S"  # Stored as base64 string

    def __init__(
        self,
        key_id: str,
        mode: EncryptionMode | None = None,
        region: str | None = None,
        context: dict[str, str] | None = None,
    ):
        """Create an encrypted attribute.

        Args:
            key_id: KMS key ID, ARN, or alias.
            mode: Encryption mode (default: ReadWrite).
            region: AWS region (optional).
            context: Encryption context dict (optional).
        """
        super().__init__(hash_key=False, range_key=False, default=None, null=True)
        self.key_id = key_id
        self.mode = mode
        self.region = region
        self.context = context
        self._encryptor: KmsEncryptor | None = None

    @property
    def encryptor(self) -> KmsEncryptor:
        """Lazy-load the KMS encryptor."""
        if self._encryptor is None:
            self._encryptor = KmsEncryptor(
                key_id=self.key_id,
                region=self.region,
                context=self.context,
            )
        return self._encryptor

    def _can_encrypt(self) -> bool:
        """Check if encryption is allowed based on mode."""
        if self.mode is None:
            return True  # Default is ReadWrite
        return self.mode != EncryptionMode.ReadOnly

    def _can_decrypt(self) -> bool:
        """Check if decryption is allowed based on mode."""
        if self.mode is None:
            return True  # Default is ReadWrite
        return self.mode != EncryptionMode.WriteOnly

    def serialize(self, value: str | None) -> str | None:
        """Encrypt value for DynamoDB.

        Args:
            value: String to encrypt.

        Returns:
            Base64-encoded ciphertext with "ENC:" prefix, or the original
            value if mode is ReadOnly.
        """
        if value is None:
            return None

        if not self._can_encrypt():
            return value  # ReadOnly mode: store as-is

        result = self.encryptor.sync_encrypt_with_metrics(value)
        _record_kms_metrics(result.metrics.duration_ms, result.metrics.kms_calls)
        return result.ciphertext

    def deserialize(self, value: Any) -> str | None:
        """Decrypt value from DynamoDB.

        Args:
            value: Encrypted value with "ENC:" prefix.

        Returns:
            Original plaintext string, or the encrypted value if mode
            is WriteOnly.
        """
        if value is None:
            return None

        if not isinstance(value, str):
            return str(value)

        # Check if encrypted
        if not KmsEncryptor.is_encrypted(value):
            return value

        if not self._can_decrypt():
            return value  # WriteOnly mode: return encrypted value

        result = self.encryptor.sync_decrypt_with_metrics(value)
        _record_kms_metrics(result.metrics.duration_ms, result.metrics.kms_calls)
        return result.plaintext
