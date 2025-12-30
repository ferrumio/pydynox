from pydynox import Model
from pydynox.attributes import CompressedAttribute, StringAttribute


class Article(Model):
    class Meta:
        table = "articles"

    pk = StringAttribute(hash_key=True)
    content = CompressedAttribute()  # Auto-compresses large text


# Create an article with large content
article = Article(
    pk="ARTICLE#123",
    content="This is a very long article..." * 1000,
)
article.save()

# When you read it back, it's automatically decompressed
loaded = Article.get(pk="ARTICLE#123")
print(loaded.content)  # Original text, not compressed
