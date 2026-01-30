"""Integration tests for OpenTelemetry tracing with real Model operations."""

from __future__ import annotations

import uuid

import pytest
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from pydynox import (
    DynamoDBClient,
    Model,
    ModelConfig,
    disable_tracing,
    enable_tracing,
    set_logger,
)
from pydynox._internal._logging import get_logger
from pydynox.attributes import StringAttribute

# Module-level exporter and provider (set once)
_exporter = InMemorySpanExporter()
_provider = TracerProvider()
_provider.add_span_processor(SimpleSpanProcessor(_exporter))
trace.set_tracer_provider(_provider)


@pytest.fixture(autouse=True)
def reset_tracing():
    """Reset tracing state and clear spans before each test."""
    disable_tracing()
    _exporter.clear()
    yield
    disable_tracing()


@pytest.fixture
def otel_exporter():
    """Provide the in-memory exporter for assertions."""
    return _exporter


@pytest.fixture
def user_model(dynamo: DynamoDBClient):
    """Create a User model for testing."""

    class User(Model):
        model_config = ModelConfig(table="test_table", client=dynamo)
        pk = StringAttribute(partition_key=True)
        sk = StringAttribute(sort_key=True)
        name = StringAttribute()

    return User


@pytest.mark.asyncio
async def test_model_save_creates_span(
    otel_exporter: InMemorySpanExporter, user_model: type[Model]
):
    """Model.save() should create a PutItem span."""
    # GIVEN tracing is enabled
    enable_tracing()

    # WHEN we save a model
    user = user_model(pk=f"USER#{uuid.uuid4()}", sk="PROFILE", name="John")
    await user.save()

    # THEN a PutItem span is created
    spans = otel_exporter.get_finished_spans()
    assert len(spans) >= 1

    put_span = next((s for s in spans if "PutItem" in s.name), None)
    assert put_span is not None
    assert put_span.attributes["db.system.name"] == "aws.dynamodb"
    assert put_span.attributes["db.operation.name"] == "PutItem"
    assert put_span.attributes["db.collection.name"] == "test_table"


@pytest.mark.asyncio
async def test_model_get_creates_span(otel_exporter: InMemorySpanExporter, user_model: type[Model]):
    """Model.get() should create a GetItem span."""
    enable_tracing()

    # GIVEN a saved user
    pk = f"USER#{uuid.uuid4()}"
    user = user_model(pk=pk, sk="PROFILE", name="Jane")
    await user.save()
    otel_exporter.clear()

    # WHEN we get the user
    result = await user_model.get(pk=pk, sk="PROFILE")
    assert result is not None

    # THEN a GetItem span is created
    spans = otel_exporter.get_finished_spans()
    assert len(spans) >= 1

    get_span = next((s for s in spans if "GetItem" in s.name), None)
    assert get_span is not None
    assert get_span.attributes["db.operation.name"] == "GetItem"


@pytest.mark.asyncio
async def test_model_delete_creates_span(
    otel_exporter: InMemorySpanExporter, user_model: type[Model]
):
    """Model.delete() should create a DeleteItem span."""
    enable_tracing()

    # GIVEN a saved user
    pk = f"USER#{uuid.uuid4()}"
    user = user_model(pk=pk, sk="PROFILE", name="Bob")
    await user.save()
    otel_exporter.clear()

    # WHEN we delete the user
    await user.delete()

    # THEN a DeleteItem span is created
    spans = otel_exporter.get_finished_spans()
    assert len(spans) >= 1

    delete_span = next((s for s in spans if "DeleteItem" in s.name), None)
    assert delete_span is not None
    assert delete_span.attributes["db.operation.name"] == "DeleteItem"


@pytest.mark.asyncio
async def test_model_update_creates_span(
    otel_exporter: InMemorySpanExporter, user_model: type[Model]
):
    """Model.save() after modification should create an UpdateItem span (smart save)."""
    enable_tracing()

    # First save a user
    pk = f"USER#{uuid.uuid4()}"
    user = user_model(pk=pk, sk="PROFILE", name="Alice")
    await user.save()

    otel_exporter.clear()

    # Now update and save again - smart save uses UpdateItem
    user.name = "Alice Updated"
    await user.save()

    spans = otel_exporter.get_finished_spans()
    assert len(spans) >= 1

    # Smart save uses UpdateItem for changed fields only
    update_span = next((s for s in spans if "UpdateItem" in s.name), None)
    assert update_span is not None
    assert update_span.attributes["db.operation.name"] == "UpdateItem"


@pytest.mark.asyncio
async def test_model_full_replace_creates_putitem_span(
    otel_exporter: InMemorySpanExporter, user_model: type[Model]
):
    """Model.save(full_replace=True) should create a PutItem span."""
    enable_tracing()

    # First save a user
    pk = f"USER#{uuid.uuid4()}"
    user = user_model(pk=pk, sk="PROFILE", name="Bob")
    await user.save()

    otel_exporter.clear()

    # Update and save with full_replace=True - forces PutItem
    user.name = "Bob Updated"
    await user.save(full_replace=True)

    spans = otel_exporter.get_finished_spans()
    assert len(spans) >= 1

    # full_replace=True forces PutItem instead of UpdateItem
    put_span = next((s for s in spans if "PutItem" in s.name), None)
    assert put_span is not None
    assert put_span.attributes["db.operation.name"] == "PutItem"


@pytest.mark.asyncio
async def test_tracing_with_prefix(otel_exporter: InMemorySpanExporter, user_model: type[Model]):
    """Tracing with prefix should add prefix to span names."""
    enable_tracing(span_name_prefix="myapp")

    user = user_model(pk=f"USER#{uuid.uuid4()}", sk="PROFILE", name="Test")
    await user.save()

    spans = otel_exporter.get_finished_spans()
    put_span = next((s for s in spans if "PutItem" in s.name), None)
    assert put_span is not None
    assert put_span.name.startswith("myapp ")


@pytest.mark.asyncio
async def test_multiple_operations_create_multiple_spans(
    otel_exporter: InMemorySpanExporter, user_model: type[Model]
):
    """Multiple operations should create multiple spans."""
    enable_tracing()

    pk = f"USER#{uuid.uuid4()}"

    # Save
    user = user_model(pk=pk, sk="PROFILE", name="Multi")
    await user.save()

    # Get
    await user_model.get(pk=pk, sk="PROFILE")

    # Save again (update)
    user.name = "Multi Updated"
    await user.save()

    # Delete
    await user.delete()

    spans = otel_exporter.get_finished_spans()
    operation_names = [s.attributes.get("db.operation.name") for s in spans]

    assert "PutItem" in operation_names
    assert "GetItem" in operation_names
    assert "DeleteItem" in operation_names


@pytest.mark.asyncio
async def test_disable_tracing_stops_spans(
    otel_exporter: InMemorySpanExporter, user_model: type[Model]
):
    """disable_tracing() should stop creating spans."""
    # GIVEN tracing is enabled and we save a user
    enable_tracing()
    user1 = user_model(pk=f"USER#{uuid.uuid4()}", sk="PROFILE", name="First")
    await user1.save()
    span_count_before = len(otel_exporter.get_finished_spans())

    # WHEN we disable tracing and save another user
    disable_tracing()
    user2 = user_model(pk=f"USER#{uuid.uuid4()}", sk="PROFILE", name="Second")
    await user2.save()
    span_count_after = len(otel_exporter.get_finished_spans())

    # THEN no new spans are created
    assert span_count_after == span_count_before


@pytest.mark.asyncio
async def test_context_propagation_parent_child_spans(
    otel_exporter: InMemorySpanExporter, user_model: type[Model]
):
    """DynamoDB spans should be children of the current active span."""
    enable_tracing()

    tracer = trace.get_tracer("test-service")

    # Create a parent span (simulating a Lambda handler or HTTP request)
    with tracer.start_as_current_span("handle_request"):
        user = user_model(pk=f"USER#{uuid.uuid4()}", sk="PROFILE", name="Context Test")
        await user.save()

        # Get the user back
        await user_model.get(pk=user.pk, sk=user.sk)

    spans = otel_exporter.get_finished_spans()

    # Find spans
    parent = next((s for s in spans if s.name == "handle_request"), None)
    put_span = next((s for s in spans if "PutItem" in s.name), None)
    get_span = next((s for s in spans if "GetItem" in s.name), None)

    assert parent is not None
    assert put_span is not None
    assert get_span is not None

    # Verify parent-child relationship
    assert put_span.parent is not None
    assert put_span.parent.span_id == parent.context.span_id

    assert get_span.parent is not None
    assert get_span.parent.span_id == parent.context.span_id


@pytest.mark.asyncio
async def test_nested_spans_share_trace_id(
    otel_exporter: InMemorySpanExporter, user_model: type[Model]
):
    """All spans in a trace should share the same trace_id."""
    enable_tracing()

    tracer = trace.get_tracer("test-service")

    with tracer.start_as_current_span("lambda_handler"):
        user = user_model(pk=f"USER#{uuid.uuid4()}", sk="PROFILE", name="Trace Test")
        await user.save()
        await user_model.get(pk=user.pk, sk=user.sk)
        await user.delete()

    spans = otel_exporter.get_finished_spans()

    # All spans should have the same trace_id
    trace_ids = {s.context.trace_id for s in spans}
    assert len(trace_ids) == 1, "All spans should share the same trace_id"


class MockLogger:
    """Mock logger for capturing log messages."""

    def __init__(self):
        self.messages: list[tuple[str, str, dict]] = []

    def info(self, msg: str, **kwargs):
        self.messages.append(("info", msg, kwargs))

    def debug(self, msg: str, **kwargs):
        self.messages.append(("debug", msg, kwargs))

    def warning(self, msg: str, **kwargs):
        self.messages.append(("warning", msg, kwargs))

    def error(self, msg: str, **kwargs):
        self.messages.append(("error", msg, kwargs))


@pytest.mark.asyncio
async def test_logs_include_trace_context(user_model: type[Model]):
    """Logs should include trace_id and span_id when tracing is enabled."""
    enable_tracing()

    original_logger = get_logger()
    mock_logger = MockLogger()
    set_logger(mock_logger)

    tracer = trace.get_tracer("test-service")

    with tracer.start_as_current_span("test_request"):
        user = user_model(pk=f"USER#{uuid.uuid4()}", sk="PROFILE", name="Log Test")
        await user.save()

    # Check that logs have trace context
    assert len(mock_logger.messages) >= 1

    _, _, kwargs = mock_logger.messages[0]
    extra = kwargs.get("extra", kwargs)

    assert "trace_id" in extra
    assert "span_id" in extra
    assert len(extra["trace_id"]) == 32  # 128-bit hex
    assert len(extra["span_id"]) == 16  # 64-bit hex

    # Cleanup
    set_logger(original_logger)
