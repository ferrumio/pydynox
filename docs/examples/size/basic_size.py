from pydynox import Model
from pydynox.attributes import StringAttribute


class User(Model):
    class Meta:
        table = "users"

    pk = StringAttribute(hash_key=True)
    sk = StringAttribute(range_key=True)
    name = StringAttribute()
    bio = StringAttribute(null=True)


user = User(pk="USER#123", sk="PROFILE", name="John", bio="Hello world!")

# Check item size
size = user.calculate_size()
print(f"Size: {size.bytes} bytes")
print(f"Size: {size.kb:.2f} KB")
print(f"Percent of limit: {size.percent:.1f}%")
print(f"Over limit: {size.is_over_limit}")
