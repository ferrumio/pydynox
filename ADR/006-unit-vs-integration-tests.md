# ADR 006: Unit tests vs Integration tests

## Status

Accepted

## Context

Need to test both isolated logic and real DynamoDB behavior.

## Decision

Maintain two test suites:

- `tests/unit/` - Fast, mocked, test isolated logic
- `tests/integration/` - Real DynamoDB (DynamoDB container), test actual behavior

## Unit tests

- Mock DynamoDB calls
- Test Python logic in isolation
- Fast (run in ~2 seconds)
- Run on every commit

```python
def test_model_validates_required_fields(mock_client):
    with pytest.raises(ValueError):
        User(name="John")  # missing pk
```

## Integration tests

- Use real DynamoDB (DynamoDB container in Docker)
- Test actual AWS SDK behavior
- Slower (~30 seconds)
- Run in CI and before releases

```python
def test_put_and_get_item(dynamo):
    dynamo.put_item("test_table", {"pk": "USER#1", "name": "John"})
    item = dynamo.get_item("test_table", {"pk": "USER#1"})
    assert item["name"] == "John"
```

## Why both?

- Unit tests catch logic bugs fast
- Integration tests catch SDK/DynamoDB behavior issues
- Unit tests run locally without Docker
- Integration tests give confidence before release

## Running tests

```bash
uv run pytest tests/unit/        # Fast, no Docker
uv run pytest tests/integration/ # Needs localstack
uv run pytest                    # All tests
```

## Consequences

- Fast feedback loop with unit tests
- Confidence with integration tests
- Need Docker for full test suite
