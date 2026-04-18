"""Tests for typed JSONAttribute with Pydantic models and dataclasses."""

import dataclasses
from typing import Any

from pydynox import Model, ModelConfig
from pydynox.attributes import JSONAttribute, StringAttribute
from pydynox.testing import MemoryBackend


@dataclasses.dataclass
class Payload:
    region: str
    score: float


class Event(Model):
    model_config = ModelConfig(table="events")
    pk = StringAttribute(partition_key=True)
    payload = JSONAttribute(Payload)


class Config(Model):
    model_config = ModelConfig(table="configs")
    pk = StringAttribute(partition_key=True)
    settings = JSONAttribute()


# --- Typed JSONAttribute with dataclass ---


def test_typed_json_model_init():
    """Typed JSONAttribute accepts dataclass on init."""
    # WHEN we create a model with a typed JSON attribute
    event = Event(pk="EVT#1", payload=Payload(region="us-east-1", score=0.95))

    # THEN the value should be the dataclass instance
    assert event.payload == Payload(region="us-east-1", score=0.95)
    assert event.payload.region == "us-east-1"


def test_typed_json_model_none():
    """Typed JSONAttribute defaults to None when not provided."""
    # WHEN we create a model without setting the JSON attribute
    event = Event(pk="EVT#1")

    # THEN it should be None
    assert event.payload is None


def test_typed_json_to_dict():
    """to_dict serializes typed JSON to JSON string."""
    # GIVEN a model with typed JSON
    event = Event(pk="EVT#1", payload=Payload(region="us-east-1", score=0.95))

    # WHEN we convert to dict
    result = event.to_dict()

    # THEN payload should be a JSON string
    assert result["payload"] == '{"region": "us-east-1", "score": 0.95}'


def test_typed_json_from_dict():
    """from_dict deserializes JSON string to typed model."""
    # GIVEN raw DynamoDB data with JSON string
    data = {"pk": "EVT#1", "payload": '{"region": "us-east-1", "score": 0.95}'}

    # WHEN we create from dict
    event = Event.from_dict(data)

    # THEN payload should be the dataclass instance
    assert event.payload == Payload(region="us-east-1", score=0.95)


def test_typed_json_from_dict_with_dict_value():
    """from_dict handles already-parsed dict (e.g., from MemoryBackend)."""
    # GIVEN raw data with dict value (not JSON string)
    data = {"pk": "EVT#1", "payload": {"region": "us-east-1", "score": 0.95}}

    # WHEN we create from dict
    event = Event.from_dict(data)

    # THEN payload should still be the dataclass instance
    assert event.payload == Payload(region="us-east-1", score=0.95)


# --- Backward compatibility ---


def test_untyped_json_still_works():
    """Untyped JSONAttribute works exactly as before."""
    # GIVEN a model with untyped JSON
    config = Config(pk="CFG#1", settings={"theme": "dark"})

    # THEN it should be a plain dict
    assert config.settings == {"theme": "dark"}

    # AND to_dict should serialize to JSON string
    result = config.to_dict()
    assert result["settings"] == '{"theme": "dark"}'


def test_untyped_json_from_dict():
    """Untyped JSONAttribute from_dict returns plain dict."""
    data = {"pk": "CFG#1", "settings": '{"theme": "dark"}'}
    config = Config.from_dict(data)

    assert config.settings == {"theme": "dark"}
    assert isinstance(config.settings, dict)


# --- In-place mutation tracking ---


def test_json_snapshots_built_on_from_dict():
    """from_dict should build JSON snapshots for typed attributes."""
    data = {"pk": "EVT#1", "payload": '{"region": "us-east-1", "score": 0.95}'}
    event = Event.from_dict(data)

    # THEN _json_snapshots should contain the typed attribute
    assert "payload" in event._json_snapshots
    assert event._json_snapshots["payload"] == '{"region": "us-east-1", "score": 0.95}'


def test_json_snapshots_empty_for_untyped():
    """Untyped JSONAttribute should not produce snapshots."""
    data = {"pk": "CFG#1", "settings": '{"theme": "dark"}'}
    config = Config.from_dict(data)

    # THEN _json_snapshots should be empty (no typed JSON attributes)
    assert config._json_snapshots == {}


def test_detect_inplace_mutation():
    """_detect_json_mutations catches in-place changes on typed JSON."""
    data = {"pk": "EVT#1", "payload": '{"region": "us-east-1", "score": 0.95}'}
    event = Event.from_dict(data)

    # GIVEN the instance is clean
    assert event.is_dirty is False

    # WHEN we mutate the payload in-place (no __setattr__ triggered on Event)
    event.payload.score = 0.99

    # AND we run mutation detection
    event._detect_json_mutations()

    # THEN the change should be detected
    assert event.is_dirty is True
    assert "payload" in event.changed_fields


def test_no_false_positive_without_mutation():
    """_detect_json_mutations should not flag unchanged attributes."""
    data = {"pk": "EVT#1", "payload": '{"region": "us-east-1", "score": 0.95}'}
    event = Event.from_dict(data)

    # WHEN we run detection without any mutation
    event._detect_json_mutations()

    # THEN it should remain clean
    assert event.is_dirty is False


def test_detect_mutation_with_none_value():
    """_detect_json_mutations handles None payload correctly."""
    data: dict[str, Any] = {"pk": "EVT#1"}
    event = Event.from_dict(data)

    # WHEN payload is None and we detect mutations
    event._detect_json_mutations()

    # THEN it should remain clean
    assert event.is_dirty is False


@MemoryBackend()
def test_inplace_mutation_detected_on_save():
    """sync_save detects in-place mutations on typed JSONAttributes."""
    # GIVEN a saved model with typed JSON
    event = Event(pk="EVT#1", payload=Payload(region="us-east-1", score=0.95))
    event.sync_save()

    # WHEN we load it and mutate in-place
    loaded = Event.sync_get(pk="EVT#1")
    loaded.payload.score = 0.99

    # AND save again
    loaded.sync_save()

    # THEN the mutation should be persisted
    result = Event.sync_get(pk="EVT#1")
    assert result.payload.score == 0.99
    assert result.payload.region == "us-east-1"


@MemoryBackend()
def test_reset_tracking_rebuilds_snapshots():
    """_reset_change_tracking should rebuild JSON snapshots."""
    event = Event(pk="EVT#1", payload=Payload(region="us-east-1", score=0.95))
    event.sync_save()

    # After save, snapshots should reflect current state
    assert "payload" in event._json_snapshots
    assert '"score": 0.95' in event._json_snapshots["payload"]

    # Mutate and save
    loaded = Event.sync_get(pk="EVT#1")
    loaded.payload.score = 0.5
    loaded.sync_save()

    # Snapshots should be updated
    assert '"score": 0.5' in loaded._json_snapshots["payload"]


@MemoryBackend()
def test_assignment_still_tracked_for_typed_json():
    """Full assignment (not in-place) is still tracked via __setattr__."""
    event = Event(pk="EVT#1", payload=Payload(region="us-east-1", score=0.95))
    event.sync_save()

    loaded = Event.sync_get(pk="EVT#1")
    loaded.payload = Payload(region="eu-west-1", score=0.5)

    assert loaded.is_dirty is True
    assert "payload" in loaded.changed_fields
