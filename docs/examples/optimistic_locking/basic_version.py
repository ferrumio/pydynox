from pydynox import Model, ModelConfig
from pydynox.attributes import StringAttribute, VersionAttribute


class Document(Model):
    model_config = ModelConfig(table="documents")
    pk = StringAttribute(hash_key=True)
    content = StringAttribute()
    version = VersionAttribute()


# Create new document
doc = Document(pk="DOC#VERSION", content="Hello")
print(doc.version)  # None

doc.save()
print(doc.version)  # 1

# Update document
doc.content = "Hello World"
doc.save()
print(doc.version)  # 2

# Load from DB - version is preserved
loaded = Document.get(pk="DOC#VERSION")
print(loaded.version)  # 2
