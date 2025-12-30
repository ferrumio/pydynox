from pydynox import Model
from pydynox.attributes import CompressedAttribute, CompressionAlgorithm, StringAttribute


class Document(Model):
    class Meta:
        table = "documents"

    pk = StringAttribute(hash_key=True)

    # Best compression ratio (default)
    body = CompressedAttribute(algorithm=CompressionAlgorithm.Zstd)

    # Fastest compression/decompression
    logs = CompressedAttribute(algorithm=CompressionAlgorithm.Lz4)

    # Good balance, widely compatible
    metadata = CompressedAttribute(algorithm=CompressionAlgorithm.Gzip)
