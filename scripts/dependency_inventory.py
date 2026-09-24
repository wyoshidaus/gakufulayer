"""Record an installed dependency-license inventory from package metadata.

This is an environment snapshot, not a reviewed license conclusion or
reproducible lockfile. Run it in isolated CI core/full installations.
"""

from __future__ import annotations

import importlib.metadata as metadata
import json
import platform
from typing import Any


def _license_markers(dist: metadata.Distribution) -> list[str]:
    expression = dist.metadata.get("License-Expression")
    if expression:
        return [expression]
    classifiers = dist.metadata.get_all("Classifier", [])
    license_classes = sorted(c for c in classifiers if c.startswith("License ::"))
    if license_classes:
        return license_classes
    legacy = (dist.metadata.get("License") or "").strip()
    if legacy and len(legacy) < 140 and "\n" not in legacy:
        return [legacy]
    return ["unknown: review package metadata and bundled LICENSE files"]


def collect_inventory() -> dict[str, Any]:
    packages: list[dict[str, Any]] = []
    for dist in metadata.distributions():
        name = dist.metadata.get("Name") or "unknown"
        packages.append({
            "name": name,
            "version": dist.version,
            "license_markers": _license_markers(dist),
        })
    packages.sort(key=lambda p: (p["name"].casefold(), p["version"]))
    return {
        "schema_version": "1.0",
        "inventory_type": "Installed CI environment snapshot; not a lockfile or license clearance",
        "python_version": platform.python_version(),
        "packages": packages,
    }


if __name__ == "__main__":
    print(json.dumps(collect_inventory(), ensure_ascii=False, indent=2))
