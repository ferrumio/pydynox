"""DatetimeAttribute example - store datetime as ISO string."""

from datetime import datetime, timezone

from pydynox import Model, ModelConfig
from pydynox.attributes import DatetimeAttribute, StringAttribute
from pydynox.hooks import before_save


class Event(Model):
    model_config = ModelConfig(table="events")

    pk = StringAttribute(hash_key=True)
    created_at = DatetimeAttribute()


# Save with datetime
event = Event(pk="EVT#1", created_at=datetime.now(timezone.utc))
event.save()
# Stored as "2024-01-15T10:30:00+00:00"

# Load it back - returns datetime object
loaded = Event.get(pk="EVT#1")
print(loaded.created_at)  # datetime object
print(loaded.created_at.year)  # 2024


# Auto-set timestamps with hooks
class Article(Model):
    model_config = ModelConfig(table="articles")

    pk = StringAttribute(hash_key=True)
    created_at = DatetimeAttribute(null=True)
    updated_at = DatetimeAttribute(null=True)

    @before_save
    def set_timestamps(self):
        now = datetime.now(timezone.utc)
        if self.created_at is None:
            self.created_at = now
        self.updated_at = now


article = Article(pk="ART#1")
article.save()
print(article.created_at)  # Auto-set on first save
print(article.updated_at)  # Updated on every save
