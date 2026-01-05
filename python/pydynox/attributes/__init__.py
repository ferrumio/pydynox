"""Attribute types for Model definitions."""

# Re-export compression/encryption enums for convenience
from pydynox._internal._compression import CompressionAlgorithm
from pydynox._internal._encryption import EncryptionMode
from pydynox._internal._s3 import S3File
from pydynox.attributes.base import Attribute
from pydynox.attributes.compressed import CompressedAttribute
from pydynox.attributes.encrypted import EncryptedAttribute
from pydynox.attributes.primitives import (
    BinaryAttribute,
    BooleanAttribute,
    ListAttribute,
    MapAttribute,
    NumberAttribute,
    StringAttribute,
)
from pydynox.attributes.s3 import S3Attribute
from pydynox.attributes.sets import NumberSetAttribute, StringSetAttribute
from pydynox.attributes.special import (
    DatetimeAttribute,
    EnumAttribute,
    JSONAttribute,
)
from pydynox.attributes.ttl import ExpiresIn, TTLAttribute
from pydynox.attributes.version import VersionAttribute

__all__ = [
    # Base
    "Attribute",
    # Primitives
    "StringAttribute",
    "NumberAttribute",
    "BooleanAttribute",
    "BinaryAttribute",
    "ListAttribute",
    "MapAttribute",
    # Sets
    "StringSetAttribute",
    "NumberSetAttribute",
    # Special
    "JSONAttribute",
    "EnumAttribute",
    "DatetimeAttribute",
    # TTL
    "TTLAttribute",
    "ExpiresIn",
    # Compressed
    "CompressedAttribute",
    "CompressionAlgorithm",
    # Encrypted
    "EncryptedAttribute",
    "EncryptionMode",
    # S3
    "S3Attribute",
    "S3File",
    # Version
    "VersionAttribute",
]
