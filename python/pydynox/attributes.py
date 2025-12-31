"""Attribute types for Model definitions."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Generic, TypeVar

from pydynox._internal._atomic import (
    AtomicAdd,
    AtomicAppend,
    AtomicIfNotExists,
    AtomicPath,
    AtomicPrepend,
    AtomicRemove,
    AtomicSet,
)
from pydynox._internal._compression import (
    CompressionAlgorithm,
    compress_string,
    decompress_string,
)
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
from pydynox._internal._encryption import EncryptionMode, KmsEncryptor

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
    # New attribute types
    "JSONAttribute",
    "EnumAttribute",
    "DatetimeAttribute",
    "StringSetAttribute",
    "NumberSetAttribute",
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
        return ConditionPath(attribute=self)

    def __eq__(self, other: Any) -> ConditionComparison:  # type: ignore[override]
        return ConditionComparison("=", self._get_path(), other)

    def __ne__(self, other: Any) -> ConditionComparison:  # type: ignore[override]
        return ConditionComparison("<>", self._get_path(), other)

    def __lt__(self, other: Any) -> ConditionComparison:
        return ConditionComparison("<", self._get_path(), other)

    def __le__(self, other: Any) -> ConditionComparison:
        return ConditionComparison("<=", self._get_path(), other)

    def __gt__(self, other: Any) -> ConditionComparison:
        return ConditionComparison(">", self._get_path(), other)

    def __ge__(self, other: Any) -> ConditionComparison:
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

    # Atomic update methods
    def _get_atomic_path(self) -> AtomicPath:
        """Get AtomicPath for this attribute."""
        return AtomicPath(attribute=self)

    def set(self, value: Any) -> AtomicSet:
        """Set attribute to a value."""
        return AtomicSet(self._get_atomic_path(), value)

    def add(self, value: int | float) -> AtomicAdd:
        """Add to a number attribute (atomic increment/decrement)."""
        return AtomicAdd(self._get_atomic_path(), value)

    def remove(self) -> AtomicRemove:
        """Remove this attribute from the item."""
        return AtomicRemove(self._get_atomic_path())

    def append(self, items: list[Any]) -> AtomicAppend:
        """Append items to a list attribute."""
        return AtomicAppend(self._get_atomic_path(), items)

    def prepend(self, items: list[Any]) -> AtomicPrepend:
        """Prepend items to a list attribute."""
        return AtomicPrepend(self._get_atomic_path(), items)

    def if_not_exists(self, value: Any) -> AtomicIfNotExists:
        """Set attribute only if it doesn't exist."""
        return AtomicIfNotExists(self._get_atomic_path(), value)


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


E = TypeVar("E", bound=Enum)


class JSONAttribute(Attribute[dict[str, Any] | list[Any]]):
    """Store dict/list as JSON string.

    Different from MapAttribute which uses DynamoDB's native Map type.
    JSONAttribute stores data as a string, which can be useful when you
    need to store complex nested structures or when you want to avoid
    DynamoDB's map limitations.

    Example:
        >>> from pydynox import Model, ModelConfig
        >>> from pydynox.attributes import StringAttribute, JSONAttribute
        >>>
        >>> class Config(Model):
        ...     model_config = ModelConfig(table="configs")
        ...     pk = StringAttribute(hash_key=True)
        ...     settings = JSONAttribute()
        >>>
        >>> config = Config(pk="CFG#1", settings={"theme": "dark", "notifications": True})
        >>> config.save()
        >>> # Stored as string '{"theme": "dark", "notifications": true}'
    """

    attr_type = "S"

    def serialize(self, value: dict[str, Any] | list[Any] | None) -> str | None:
        """Convert dict/list to JSON string.

        Args:
            value: Dict or list to serialize.

        Returns:
            JSON string or None.
        """
        if value is None:
            return None
        return json.dumps(value)

    def deserialize(self, value: Any) -> dict[str, Any] | list[Any] | None:
        """Convert JSON string back to dict/list.

        Args:
            value: JSON string from DynamoDB.

        Returns:
            Parsed dict/list or None.
        """
        if value is None:
            return None
        if isinstance(value, (dict, list)):
            return value
        result: dict[str, Any] | list[Any] = json.loads(value)
        return result


class EnumAttribute(Attribute[E], Generic[E]):
    """Store Python enum as string.

    Stores the enum's value (not name) in DynamoDB. On load, converts
    back to the enum type.

    Args:
        enum_class: The Enum class to use.
        hash_key: True if this is the partition key.
        range_key: True if this is the sort key.
        default: Default enum value.
        null: Whether None is allowed.

    Example:
        >>> from enum import Enum
        >>> from pydynox import Model, ModelConfig
        >>> from pydynox.attributes import StringAttribute, EnumAttribute
        >>>
        >>> class Status(Enum):
        ...     PENDING = "pending"
        ...     ACTIVE = "active"
        >>>
        >>> class User(Model):
        ...     model_config = ModelConfig(table="users")
        ...     pk = StringAttribute(hash_key=True)
        ...     status = EnumAttribute(Status, default=Status.PENDING)
        >>>
        >>> user = User(pk="USER#1", status=Status.ACTIVE)
        >>> user.save()
        >>> # Stored as "active", loaded as Status.ACTIVE
    """

    attr_type = "S"

    def __init__(
        self,
        enum_class: type[E],
        hash_key: bool = False,
        range_key: bool = False,
        default: E | None = None,
        null: bool = True,
    ):
        """Create an enum attribute.

        Args:
            enum_class: The Enum class to use.
            hash_key: True if this is the partition key.
            range_key: True if this is the sort key.
            default: Default enum value.
            null: Whether None is allowed.
        """
        super().__init__(
            hash_key=hash_key,
            range_key=range_key,
            default=default,
            null=null,
        )
        self.enum_class = enum_class

    def serialize(self, value: E | None) -> str | None:
        """Convert enum to its string value.

        Args:
            value: Enum member.

        Returns:
            The enum's value as string.
        """
        if value is None:
            return None
        return str(value.value)

    def deserialize(self, value: Any) -> E | None:
        """Convert string back to enum.

        Args:
            value: String value from DynamoDB.

        Returns:
            Enum member.
        """
        if value is None:
            return None
        return self.enum_class(value)


class DatetimeAttribute(Attribute[datetime]):
    """Store datetime as ISO 8601 string.

    Stores datetime in ISO format which is sortable as a string.
    Naive datetimes (without timezone) are treated as UTC.

    Example:
        >>> from datetime import datetime, timezone
        >>> from pydynox import Model, ModelConfig
        >>> from pydynox.attributes import StringAttribute, DatetimeAttribute
        >>>
        >>> class Event(Model):
        ...     model_config = ModelConfig(table="events")
        ...     pk = StringAttribute(hash_key=True)
        ...     created_at = DatetimeAttribute()
        >>>
        >>> event = Event(pk="EVT#1", created_at=datetime.now(timezone.utc))
        >>> event.save()
        >>> # Stored as "2024-01-15T10:30:00+00:00"

    Note:
        For auto-set timestamps, use hooks:

        >>> from pydynox.hooks import before_save
        >>>
        >>> class Event(Model):
        ...     model_config = ModelConfig(table="events")
        ...     pk = StringAttribute(hash_key=True)
        ...     created_at = DatetimeAttribute(null=True)
        ...
        ...     @before_save
        ...     def set_created_at(self):
        ...         if self.created_at is None:
        ...             self.created_at = datetime.now(timezone.utc)
    """

    attr_type = "S"

    def serialize(self, value: datetime | None) -> str | None:
        """Convert datetime to ISO 8601 string.

        Args:
            value: datetime object.

        Returns:
            ISO format string.
        """
        if value is None:
            return None
        # Treat naive datetime as UTC
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.isoformat()

    def deserialize(self, value: Any) -> datetime | None:
        """Convert ISO string back to datetime.

        Args:
            value: ISO format string from DynamoDB.

        Returns:
            datetime object.
        """
        if value is None:
            return None
        return datetime.fromisoformat(value)


class StringSetAttribute(Attribute[set[str]]):
    """DynamoDB native string set (SS).

    Stores a set of unique strings. DynamoDB sets don't allow duplicates
    and don't preserve order.

    Example:
        >>> from pydynox import Model, ModelConfig
        >>> from pydynox.attributes import StringAttribute, StringSetAttribute
        >>>
        >>> class User(Model):
        ...     model_config = ModelConfig(table="users")
        ...     pk = StringAttribute(hash_key=True)
        ...     tags = StringSetAttribute()
        >>>
        >>> user = User(pk="USER#1", tags={"admin", "verified"})
        >>> user.save()
    """

    attr_type = "SS"

    def serialize(self, value: set[str] | None) -> list[str] | None:
        """Convert set to list for DynamoDB.

        Args:
            value: Set of strings.

        Returns:
            List of strings or None.
        """
        if value is None or len(value) == 0:
            return None
        return list(value)

    def deserialize(self, value: Any) -> set[str]:
        """Convert list back to set.

        Args:
            value: List from DynamoDB.

        Returns:
            Set of strings.
        """
        if value is None:
            return set()
        return set(value)


class NumberSetAttribute(Attribute[set[int | float]]):
    """DynamoDB native number set (NS).

    Stores a set of unique numbers. DynamoDB sets don't allow duplicates
    and don't preserve order.

    Example:
        >>> from pydynox import Model, ModelConfig
        >>> from pydynox.attributes import StringAttribute, NumberSetAttribute
        >>>
        >>> class User(Model):
        ...     model_config = ModelConfig(table="users")
        ...     pk = StringAttribute(hash_key=True)
        ...     scores = NumberSetAttribute()
        >>>
        >>> user = User(pk="USER#1", scores={100, 95, 88})
        >>> user.save()
    """

    attr_type = "NS"

    def serialize(self, value: set[int | float] | None) -> list[str] | None:
        """Convert set to list of strings for DynamoDB.

        Args:
            value: Set of numbers.

        Returns:
            List of number strings or None.
        """
        if value is None or len(value) == 0:
            return None
        return [str(v) for v in value]

    def deserialize(self, value: Any) -> set[int | float]:
        """Convert list of strings back to set of numbers.

        Args:
            value: List of number strings from DynamoDB.

        Returns:
            Set of numbers.
        """
        if value is None:
            return set()
        result: set[int | float] = set()
        for v in value:
            num = float(v)
            # Return int if it's a whole number
            if num.is_integer():
                result.add(int(num))
            else:
                result.add(num)
        return result
