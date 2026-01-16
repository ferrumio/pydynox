"""Optimistic locking with version attribute."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydynox._internal._conditions import ConditionPath
from pydynox.attributes.version import VersionAttribute

if TYPE_CHECKING:
    from pydynox.conditions import Condition
    from pydynox.model import Model


def _get_version_attr_name(self: Model) -> str | None:
    """Get the name of the version attribute if defined."""
    for attr_name, attr in self._attributes.items():
        if isinstance(attr, VersionAttribute):
            return attr_name
    return None


def _build_version_condition(self: Model) -> tuple[Condition | None, int]:
    """Build condition for optimistic locking.

    Returns:
        Tuple of (condition, new_version).
        If no version attribute, returns (None, 0).
    """
    version_attr = self._get_version_attr_name()
    if version_attr is None:
        return None, 0

    current_version: int | None = getattr(self, version_attr, None)
    path = ConditionPath(path=[version_attr])

    if current_version is None:
        return path.not_exists(), 1
    else:
        return path == current_version, current_version + 1
