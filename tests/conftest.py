"""Fixtures shared by unit and integration tests."""

import runpy
from pathlib import Path

import pytest


@pytest.fixture
def agent_skill_examples():
    """Load a fresh model so each example uses the current test client."""
    path = Path(__file__).resolve().parents[1] / "skills/using-pydynox/examples/application.py"
    return runpy.run_path(str(path))
