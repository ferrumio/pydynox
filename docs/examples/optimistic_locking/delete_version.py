from pydynox import Model, ModelConfig
from pydynox.attributes import StringAttribute, VersionAttribute
from pydynox.exceptions import ConditionalCheckFailedException


class Document(Model):
    model_config = ModelConfig(table="documents")
    pk = StringAttribute(hash_key=True)
    content = StringAttribute()
    version = VersionAttribute()


# Create and update document
doc = Document(pk="DOC#DELETE", content="Hello")
doc.save()
doc.content = "Updated"
doc.save()
print(f"Version: {doc.version}")  # 2

# Load stale copy
stale = Document.get(pk="DOC#DELETE")

# Update again
doc.content = "Updated again"
doc.save()
print(f"Version: {doc.version}")  # 3

# Try to delete with stale version - fails!
try:
    stale.delete()
except ConditionalCheckFailedException:
    print("Can't delete - version mismatch")

# Delete with current version - succeeds
doc.delete()
print("Deleted successfully")
