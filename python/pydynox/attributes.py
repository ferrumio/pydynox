"""Attribute types for Model definitions."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Any, Generic, TypeVar

from pydynox._internal._compression import (
    CompressionAlgorithm,
    compress_string,
    decompress_string,
)
from pydynox._internal._encryption import EncryptionMode, KmsEncryptor

if TYPE_CHECKING:
    from pydynox._internal._conditions import (
        ConditionBeginsWith,
        ConditionBetween,
        ConditionComparison,
        ConditionContains,
        ConditionExists,
        ConditionIn,
        ConditionNotExists,
        ConditionPath,
    )

T = TypeVar("T")

__all__ = [
    "Attribute",
    "StringAttribute",
    "NumberAttribute",
    "BooleanAttribute",
    "BinaryAttribute",
    "ListAttribute",
    "MapAttribute",
    "TTLAttribute",
    "ExpiresIn",
    "CompressedAttribute",
    "CompressionAlgorithm",
    "EncryptedAttribute",
    "EncryptionMode",
]


class Attribute(Generic[T]):
    """Base attribute class for Model fields.

    Attributes define the schema of a DynamoDB item. They can be marked
    as hash_key or range_key to define the table's primary key.

    Example:
        >>> class User(Model):
        ...     pk = StringAttribute(hash_key=True)
        ...     sk = StringAttribute(range_key=True)
        ...     name = StringAttribute()
        ...     age = NumberAttribute()
    """

    attr_type: str = "S"  # Default to string

    def __init__(
        self,
        hash_key: bool = False,
        range_key: bool = False,
        default: T | None = None,
        null: bool = True,
    ):
        """Create an attribute.

        Args:
            hash_key: True if this is the partition key.
            range_key: True if this is the sort key.
            default: Default value when not provided.
            null: Whether None is allowed.
        """
        self.hash_key = hash_key
        self.range_key = range_key
        self.default = default
        self.null = null
        self.attr_name: str | None = None

    def serialize(self, value: T | None) -> Any:
        """Convert Python value to DynamoDB format."""
        return value

    def deserialize(self, value: Any) -> T | None:
        """Convert DynamoDB value to Python format."""
        return value  # type: ignore[no-any-return]

    # Condition operators
    def _get_path(self) -> ConditionPath:
        """Get ConditionPath for this attribute."""
        from pydynox._internal._conditions import ConditionPath

        return ConditionPath(attribute=self)

    def __eq__(self, other: Any) -> ConditionComparison:  # type: ignore[override]
        from pydynox._internal._conditions import ConditionComparison

        return ConditionComparison("=", self._get_path(), other)

    def __ne__(self, other: Any) -> ConditionComparison:  # type: ignore[override]
        from pydynox._internal._conditions import ConditionComparison

        return ConditionComparison("<>", self._get_path(), other)

    def __lt__(self, other: Any) -> ConditionComparison:
        from pydynox._internal._conditions import ConditionComparison

        return ConditionComparison("<", self._get_path(), other)

    def __le__(self, other: Any) -> ConditionComparison:
        from pydynox._internal._conditions import ConditionComparison

        return ConditionComparison("<=", self._get_path(), other)

    def __gt__(self, other: Any) -> ConditionComparison:
        from pydynox._internal._conditions import ConditionComparison

        return ConditionComparison(">", self._get_path(), other)

    def __ge__(self, other: Any) -> ConditionComparison:
        from pydynox._internal._conditions import ConditionComparison

        return ConditionComparison(">=", self._get_path(), other)

    def __getitem__(self, key: str | int) -> ConditionPath:
        """Access nested map key or list index for conditions."""
        return self._get_path()[key]

    def exists(self) -> ConditionExists:
        """Check if attribute exists."""
        return self._get_path().exists()

    def does_not_exist(self) -> ConditionNotExists:
        """Check if attribute does not exist."""
        return self._get_path().does_not_exist()

    def begins_with(self, prefix: str) -> ConditionBeginsWith:
        """Check if string attribute starts with prefix."""
        return self._get_path().begins_with(prefix)

    def contains(self, value: Any) -> ConditionContains:
        """Check if list/set contains value or string contains substring."""
        return self._get_path().contains(value)

    def between(self, lower: Any, upper: Any) -> ConditionBetween:
        """Check if value is between lower and upper (inclusive)."""
        return self._get_path().between(lower, upper)

    def is_in(self, *values: Any) -> ConditionIn:
        """Check if value is in the given list."""
        return self._get_path().is_in(*values)


class StringAttribute(Attribute[str]):
    """String attribute (DynamoDB type S)."""

    attr_type = "S"


class NumberAttribute(Attribute[float]):
    """Number attribute (DynamoDB type N).

    Stores both int and float values.
    """

    attr_type = "N"


class BooleanAttribute(Attribute[bool]):
    """Boolean attribute (DynamoDB type BOOL)."""

    attr_type = "BOOL"


class BinaryAttribute(Attribute[bytes]):
    """Binary attribute (DynamoDB type B)."""

    attr_type = "B"


class ListAttribute(Attribute[list[Any]]):
    """List attribute (DynamoDB type L)."""

    attr_type = "L"


class MapAttribute(Attribute[dict[str, Any]]):
    """Map attribute (DynamoDB type M)."""

    attr_type = "M"


class ExpiresIn:
    """Helper class to create TTL datetime values.

    Makes it easy to set expiration times without manual datetime math.

    Example:
        >>> from pydynox.attributes import ExpiresIn
        >>> expires = ExpiresIn.hours(1)  # 1 hour from now
        >>> expires = ExpiresIn.days(7)   # 7 days from now
    """

    @staticmethod
    def seconds(n: int) -> datetime:
        """Return datetime n seconds from now.

        Args:
            n: Number of seconds.

        Returns:
            datetime in UTC.
        """
        return datetime.now(timezone.utc) + timedelta(seconds=n)

    @staticmethod
    def minutes(n: int) -> datetime:
        """Return datetime n minutes from now.

        Args:
            n: Number of minutes.

        Returns:
            datetime in UTC.
        """
        return datetime.now(timezone.utc) + timedelta(minutes=n)

    @staticmethod
    def hours(n: int) -> datetime:
        """Return datetime n hours from now.

        Args:
            n: Number of hours.

        Returns:
            datetime in UTC.
        """
        return datetime.now(timezone.utc) + timedelta(hours=n)

    @staticmethod
    def days(n: int) -> datetime:
        """Return datetime n days from now.

        Args:
            n: Number of days.

        Returns:
            datetime in UTC.
        """
        return datetime.now(timezone.utc) + timedelta(days=n)

    @staticmethod
    def weeks(n: int) -> datetime:
        """Return datetime n weeks from now.

        Args:
            n: Number of weeks.

        Returns:
            datetime in UTC.
        """
        return datetime.now(timezone.utc) + timedelta(weeks=n)


class TTLAttribute(Attribute[datetime]):
    """TTL attribute for DynamoDB Time-To-Live.

    Stores datetime as epoch timestamp (number). DynamoDB uses this
    to auto-delete expired items.

    Example:
        >>> from pydynox import Model, ModelConfig
        >>> from pydynox.attributes import StringAttribute, TTLAttribute, ExpiresIn
        >>>
        >>> class Session(Model):
        ...     model_config = ModelConfig(table="sessions")
        ...     pk = StringAttribute(hash_key=True)
        ...     expires_at = TTLAttribute()
        >>>
        >>> session = Session(pk="SESSION#123", expires_at=ExpiresIn.hours(1))
        >>> session.save()
    """

    attr_type = "N"

    def serialize(self, value: datetime | None) -> int | None:
        """Convert datetime to epoch timestamp.

        Args:
            value: datetime object.

        Returns:
            Unix timestamp as integer.
        """
        if value is None:
            return None
        return int(value.timestamp())

    def deserialize(self, value: Any) -> datetime:
        """Convert epoch timestamp to datetime.

        Args:
            value: Unix timestamp (int or float).

        Returns:
            datetime object in UTC.
        """
        return datetime.fromtimestamp(float(value), tz=timezone.utc)


class CompressedAttribute(Attribute[str]):
    """Attribute that auto-compresses large text values.

    Stores data as base64-encoded compressed binary in DynamoDB.
    Compression happens automatically on save, decompression on load.
    All heavy work (compression + base64) is done in Rust for speed.

    Args:
        algorithm: Compression algorithm to use. Options:
            - CompressionAlgorithm.Zstd (default): Best compression ratio
            - CompressionAlgorithm.Lz4: Fastest
            - CompressionAlgorithm.Gzip: Good balance
        level: Compression level. Higher = smaller but slower.
            - zstd: 1-22 (default 3)
            - gzip: 0-9 (default 6)
            - lz4: ignored
        min_size: Minimum size in bytes to compress (default 100).
            Smaller values are stored as-is.
        threshold: Compression ratio threshold (default 0.9).
            Only compress if result is smaller by this ratio.
        hash_key: True if this is the partition key.
        range_key: True if this is the sort key.
        default: Default value when not provided.
        null: Whether None is allowed.

    Example:
        >>> from pydynox import Model, ModelConfig
        >>> from pydynox.attributes import StringAttribute, CompressedAttribute
        >>>
        >>> class Document(Model):
        ...     model_config = ModelConfig(table="documents")
        ...     pk = StringAttribute(hash_key=True)
        ...     body = CompressedAttribute()  # Uses zstd by default
        ...     logs = CompressedAttribute(algorithm=CompressionAlgorithm.Lz4)
    """

    attr_type = "S"  # Stored as base64 string

    def __init__(
        self,
        algorithm: CompressionAlgorithm | None = None,
        level: int | None = None,
        min_size: int = 100,
        threshold: float = 0.9,
        hash_key: bool = False,
        range_key: bool = False,
        default: str | None = None,
        null: bool = True,
    ):
        """Create a compressed attribute.

        Args:
            algorithm: Compression algorithm (default: zstd).
            level: Compression level.
            min_size: Minimum bytes to trigger compression.
            threshold: Only compress if ratio is below this.
            hash_key: True if this is the partition key.
            range_key: True if this is the sort key.
            default: Default value when not provided.
            null: Whether None is allowed.
        """
        super().__init__(
            hash_key=hash_key,
            range_key=range_key,
            default=default,
            null=null,
        )
        self.algorithm = algorithm
        self.level = level
        self.min_size = min_size
        self.threshold = threshold

    def serialize(self, value: str | None) -> str | None:
        """Compress and encode value for DynamoDB.

        Args:
            value: String to compress.

        Returns:
            Base64-encoded compressed data with prefix, or original if
            compression not worthwhile.
        """
        if value is None:
            return None

        # All done in Rust: compression + base64 + prefix
        return compress_string(
            value,
            self.algorithm,
            self.level,
            self.min_size,
            self.threshold,
        )

    def deserialize(self, value: Any) -> str | None:
        """Decompress value from DynamoDB.

        Args:
            value: Stored value (may be compressed or plain).

        Returns:
            Original string.
        """
        if value is None:
            return None

        if not isinstance(value, str):
            return str(value)

        # All done in Rust: detect prefix + base64 decode + decompress
        return decompress_string(value)


class EncryptedAttribute(Attribute[str]):
    """Attribute that encrypts values using AWS KMS.

    Encrypts sensitive data like SSN or credit cards at the field level.
    Encryption happens on save, decryption on load.

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

        return self.encryptor.encrypt(value)

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

        return self.encryptor.decrypt(value)
