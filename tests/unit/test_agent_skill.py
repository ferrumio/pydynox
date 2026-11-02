"""Exercise the consumer skill examples and check their reference targets."""

import inspect
import re
from pathlib import Path
from urllib.parse import urlsplit
from uuid import uuid4

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_SKILL = _ROOT / "skills/using-pydynox"


@pytest.mark.parametrize(
    "operation", ["crud", "sync_crud", "query_and_batch", "sync_query_and_batch"]
)
async def test_agent_skill_memory_examples(pydynox_memory_backend, agent_skill_examples, operation):
    # GIVEN the installed memory fixture and the skill's actual example code
    # WHEN an application workflow runs through the public API
    result = agent_skill_examples[operation](uuid4().hex)
    if inspect.isawaitable(result):
        await result
    # THEN the workflow's read-back assertions passed without AWS


@pytest.mark.parametrize("markdown", sorted(_SKILL.rglob("*.md")), ids=lambda p: p.name)
def test_agent_skill_reference_targets_exist(markdown):
    # GIVEN links that must survive copying the skill into another application
    links = re.findall(r"\[[^\]\n]+\]\(([^)]+)\)", markdown.read_text())
    for link in links:
        url = urlsplit(link)
        if not url.scheme and url.path:
            target = (markdown.parent / url.path).resolve()
            # THEN local resources stay inside the installed skill and exist
            assert target.is_relative_to(_SKILL.resolve()), link
            assert target.is_file(), link
        elif url.netloc == "ferrumio.github.io" and url.path.startswith("/pydynox/guides/"):
            # AND linked guides have a maintained source in this repository
            relative = url.path.removeprefix("/pydynox/").rstrip("/")
            assert (_ROOT / "docs" / f"{relative}.md").is_file(), link
