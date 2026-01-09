from pydynox import Model, ModelConfig
from pydynox.attributes import StringAttribute, VersionAttribute
from pydynox.exceptions import ConditionCheckFailedError


class Document(Model):
    model_config = ModelConfig(table="documents")
    pk = StringAttribute(hash_key=True)
    content = StringAttribute()
    version = VersionAttribute()


# Create document
doc = Document(pk="DOC#CONCURRENT", content="Original")
doc.save()

# Two processes load the same document
process_a = Document.get(pk="DOC#CONCURRENT")
process_b = Document.get(pk="DOC#CONCURRENT")

# Both have version 1
print(process_a.version)  # 1
print(process_b.version)  # 1

# Process A updates first - succeeds
process_a.content = "Updated by A"
process_a.save()
print(process_a.version)  # 2

# Process B tries to update - fails!
process_b.content = "Updated by B"
try:
    process_b.save()
except ConditionCheckFailedError:
    print("Conflict! Someone else updated the document.")
