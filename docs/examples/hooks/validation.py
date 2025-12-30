from pydynox import Model
from pydynox.attributes import StringAttribute
from pydynox.hooks import after_save, before_save


class User(Model):
    class Meta:
        table = "users"

    pk = StringAttribute(hash_key=True)
    email = StringAttribute()
    name = StringAttribute()

    @before_save
    def validate_email(self):
        if not self.email or "@" not in self.email:
            raise ValueError("Invalid email")

    @before_save
    def normalize(self):
        self.email = self.email.lower().strip()
        self.name = self.name.strip()

    @after_save
    def log_save(self):
        print(f"Saved user: {self.pk}")


# Hooks run automatically
user = User(pk="USER#1", email="JOHN@TEST.COM", name="john doe")
user.save()  # Validates, normalizes, then logs

# Skip hooks if needed
user.save(skip_hooks=True)
