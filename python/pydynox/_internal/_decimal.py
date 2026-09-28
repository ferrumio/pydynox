"""Per-request selection of exact numeric fields."""

from __future__ import annotations

from typing import Any

DecimalFields = set[str] | frozenset[str]


def decimal_options(fields: DecimalFields | None) -> dict[str, Any]:
    """Forward the decoding option only when a request needs it."""
    return {"decimal_fields": fields} if fields else {}
