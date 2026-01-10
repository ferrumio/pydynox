"""Version information for pydynox."""

from __future__ import annotations

import platform
import sys
from importlib.metadata import version

__all__ = ["VERSION", "version_info"]

VERSION = version("pydynox")


def version_info() -> str:
    """Return complete version information for pydynox and its dependencies."""
    import importlib.metadata

    # Packages related to pydynox usage
    package_names = {
        "boto3",
        "botocore",
        "pydantic",
        "typing_extensions",
    }
    related_packages = []

    for dist in importlib.metadata.distributions():
        name = dist.metadata["Name"]
        if name in package_names:
            related_packages.append(f"{name}-{dist.version}")

    info = {
        "pydynox version": VERSION,
        "python version": sys.version,
        "platform": platform.platform(),
        "related packages": " ".join(sorted(related_packages)) or "none",
    }
    return "\n".join(
        "{:>30} {}".format(k + ":", str(v).replace("\n", " ")) for k, v in info.items()
    )
