from pydynox import Model, ModelConfig
from pydynox.attributes import CompressedAttribute, CompressionAlgorithm, StringAttribute


class Document(Model):
    model_config = ModelConfig(table="documents")

    pk = StringAttribute(partition_key=True)

    # Best compression ratio (default)
    body = CompressedAttribute(algorithm=CompressionAlgorithm.Zstd)

    # Fastest compression/decompression
    logs = CompressedAttribute(algorithm=CompressionAlgorithm.Lz4)

    # Good balance, widely compatible
    metadata = CompressedAttribute(algorithm=CompressionAlgorithm.Gzip)
