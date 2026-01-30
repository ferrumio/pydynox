from pydynox import Model
from pydynox.attributes import ListAttribute, MapAttribute, StringAttribute


class Document(Model):
    class Meta:
        table = "documents"

    pk = StringAttribute(partition_key=True)
    title = StringAttribute()
    body = StringAttribute()
    tags = ListAttribute()
    metadata = MapAttribute()


doc = Document(
    pk="DOC#1",
    title="My Document",
    body="A" * 10000,  # Large body
    tags=["draft", "important"],
    metadata={"author": "John", "version": 1},
)

# Get detailed breakdown
size = doc.calculate_size(detailed=True)

print(f"Total: {size.bytes} bytes\n")
print("Per field:")
for field, bytes in sorted(size.fields.items(), key=lambda x: -x[1]):
    print(f"  {field}: {bytes} bytes")
