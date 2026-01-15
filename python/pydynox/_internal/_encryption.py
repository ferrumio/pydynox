"""Internal encryption functions. Do not use directly."""

from __future__ import annotations

from enum import IntEnum

from pydynox import pydynox_core

KmsEncryptor = pydynox_core.KmsEncryptor
KmsMetrics = pydynox_core.KmsMetrics
EncryptResult = pydynox_core.EncryptResult
DecryptResult = pydynox_core.DecryptResult


class EncryptionMode(IntEnum):
    """Encryption mode for field-level encryption.

    Controls which operations are allowed on encrypted fields.
    """

    ReadWrite = 0  # Can encrypt and decrypt (default)
    WriteOnly = 1  # Can only encrypt
    ReadOnly = 2  # Can only decrypt
