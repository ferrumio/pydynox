from pydynox import Model, ModelConfig
from pydynox.attributes import StringAttribute, VersionAttribute
from pydynox.exceptions import ConditionalCheckFailedException


class Document(Model):
    model_config = ModelConfig(table="documents")
    pk = StringAttribute(hash_key=True)
    status = StringAttribute()
    content = StringAttribute()
    version = VersionAttribute()


# Create document
doc = Document(pk="DOC#CONDITION", status="draft", content="Hello")
doc.save()

# Update only if status is "draft"
# This combines with version check: (status = "draft" AND version = 1)
doc.content = "Updated content"
doc.save(condition=Document.status == "draft")
print(f"Updated! Version: {doc.version}")  # 2

# Change status
doc.status = "published"
doc.save()
print(f"Published! Version: {doc.version}")  # 3

# Try to update draft-only - fails because status is "published"
doc.content = "Another update"
try:
    doc.save(condition=Document.status == "draft")
except ConditionalCheckFailedException:
    print("Can't update - not a draft")
