"""Async integration tests for KMS encryption.

Minimal tests to validate async API works. Full coverage is in test_kms_encryption.py.
"""

import pytest
from pydynox._internal._encryption import KmsEncryptor


@pytest.mark.asyncio
async def test_async_encrypt_decrypt_roundtrip(localstack_endpoint, kms_key_id):
    """Async encrypt then decrypt returns original value."""
    # GIVEN a KMS encryptor
    encryptor = KmsEncryptor(
        key_id=kms_key_id,
        endpoint_url=localstack_endpoint,
        access_key="testing",
        secret_key="testing",
        region="us-east-1",
    )

    # WHEN we encrypt and decrypt async
    plaintext = "my secret data"
    result = await encryptor.encrypt(plaintext)
    decrypted_result = await encryptor.decrypt(result.ciphertext)

    # THEN we get the original value back
    assert decrypted_result.plaintext == plaintext
    assert result.ciphertext.startswith("ENC:")


@pytest.mark.asyncio
async def test_async_encrypt_with_metrics(localstack_endpoint, kms_key_id):
    """Async encrypt returns metrics."""
    # GIVEN a KMS encryptor
    encryptor = KmsEncryptor(
        key_id=kms_key_id,
        endpoint_url=localstack_endpoint,
        access_key="testing",
        secret_key="testing",
        region="us-east-1",
    )

    # WHEN we encrypt async
    result = await encryptor.encrypt_with_metrics("secret data")

    # THEN we get ciphertext and metrics
    assert result.ciphertext.startswith("ENC:")
    assert result.metrics.kms_calls == 1
    assert result.metrics.duration_ms > 0


@pytest.mark.asyncio
async def test_async_decrypt_with_metrics(localstack_endpoint, kms_key_id):
    """Async decrypt returns metrics."""
    # GIVEN a KMS encryptor and encrypted data
    encryptor = KmsEncryptor(
        key_id=kms_key_id,
        endpoint_url=localstack_endpoint,
        access_key="testing",
        secret_key="testing",
        region="us-east-1",
    )
    encrypt_result = await encryptor.encrypt("secret data")

    # WHEN we decrypt async
    result = await encryptor.decrypt_with_metrics(encrypt_result.ciphertext)

    # THEN we get plaintext and metrics
    assert result.plaintext == "secret data"
    assert result.metrics.kms_calls == 1
    assert result.metrics.duration_ms > 0


@pytest.mark.asyncio
async def test_async_encrypt_large_data(localstack_endpoint, kms_key_id):
    """Async encrypt handles large data (over KMS 4KB limit)."""
    # GIVEN a KMS encryptor
    encryptor = KmsEncryptor(
        key_id=kms_key_id,
        endpoint_url=localstack_endpoint,
        access_key="testing",
        secret_key="testing",
        region="us-east-1",
    )

    # WHEN we encrypt 100KB of data async
    plaintext = "x" * 100_000
    result = await encryptor.encrypt(plaintext)
    decrypted = await encryptor.decrypt(result.ciphertext)

    # THEN it works
    assert decrypted.plaintext == plaintext


@pytest.mark.asyncio
async def test_async_encryption_context(localstack_endpoint, kms_key_id):
    """Async encryption with context works."""
    # GIVEN a KMS encryptor with context
    context = {"tenant": "acme", "purpose": "test"}
    encryptor = KmsEncryptor(
        key_id=kms_key_id,
        endpoint_url=localstack_endpoint,
        access_key="testing",
        secret_key="testing",
        region="us-east-1",
        context=context,
    )

    # WHEN we encrypt and decrypt async
    plaintext = "secret with context"
    result = await encryptor.encrypt(plaintext)
    decrypted = await encryptor.decrypt(result.ciphertext)

    # THEN it works
    assert decrypted.plaintext == plaintext
