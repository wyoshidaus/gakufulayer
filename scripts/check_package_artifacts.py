"""Validate GakufuLayer wheel/sdist license metadata and dependency boundaries.

Pure standard library, so the check runs against built release artifacts
rather than requiring GakufuLayer or the PDF backend to be installed.
It verifies packaging evidence only; it is not a legal release approval.
"""

from __future__ import annotations

import argparse
from email.parser import Parser
import hashlib
import json
from pathlib import Path
import re
import tarfile
from typing import Any
import zipfile


def _require_single(paths: list[str], kind: str) -> str:
    if len(paths) != 1:
        raise ValueError(f"Expected exactly one {kind}; found {len(paths)}")
    return paths[0]


def _base_package(requirement: str) -> str:
    return re.split(r"[<>=!~;\[\s]", requirement.strip(), maxsplit=1)[0].lower().replace("_", "-")


def check_distributions(
    wheel_path: str | Path,
    sdist_path: str | Path,
    source_license: str | Path,
) -> dict[str, Any]:
    """Check wheel/sdist licenses and ensure PyMuPDF is never a base dependency."""
    wheel_path = Path(wheel_path)
    sdist_path = Path(sdist_path)
    expected_license = Path(source_license).read_bytes()
    expected_hash = hashlib.sha256(expected_license).hexdigest()
    checks: list[dict[str, str]] = []

    with zipfile.ZipFile(wheel_path) as wheel:
        names = wheel.namelist()
        metadata_name = _require_single(
            [n for n in names if n.endswith(".dist-info/METADATA")],
            "wheel METADATA",
        )
        metadata_record = Parser().parsestr(wheel.read(metadata_name).decode("utf-8"))
        if metadata_record.get("Name", "").lower().replace("_", "-") != "gakufulayer":
            raise ValueError("Wheel package name is not GakufuLayer")
        version = metadata_record.get("Version", "").strip()
        if not version:
            raise ValueError("Wheel is missing a version")
        expression = metadata_record.get("License-Expression")
        if expression != "Apache-2.0":
            raise ValueError("Expected wheel License-Expression: Apache-2.0")
        checks.append({"name": "wheel_spdx_expression", "status": "pass"})

        license_entries = metadata_record.get_all("License-File", [])
        if "LICENSE" not in license_entries:
            raise ValueError("Wheel metadata does not declare License-File: LICENSE")
        wheel_licenses = [
            n for n in names
            if n.endswith(".dist-info/licenses/LICENSE")
        ]
        license_name = _require_single(wheel_licenses, "wheel bundled LICENSE")
        if hashlib.sha256(wheel.read(license_name)).hexdigest() != expected_hash:
            raise ValueError("Wheel LICENSE differs from the source repository")
        checks.append({"name": "wheel_license_text", "status": "pass"})

        requirements = metadata_record.get_all("Requires-Dist", [])
        core = []
        extras: dict[str, list[str]] = {}
        for requirement in requirements:
            package = _base_package(requirement)
            condition = requirement.partition(";")[2].lower()
            match = re.search(r"extra\s*==\s*['\"]([a-z0-9_-]+)['\"]", condition)
            if condition and match is None:
                # We do not want to mistake platform/conditional requirements
                # for unconditional runtime dependencies.
                raise ValueError(f"Unsupported dependency marker: {requirement}")
            if match:
                extras.setdefault(match.group(1), []).append(package)
            else:
                core.append(package)
        if "pypdf" not in core:
            raise ValueError("pypdf must be a core requirement")
        if "pymupdf" in core:
            raise ValueError("PyMuPDF must not be an unconditional requirement")
        if "pymupdf" not in extras.get("pdf", []):
            raise ValueError("PyMuPDF must be restricted to the [pdf] extra")
        if any("pymupdf" in pkgs for key, pkgs in extras.items() if key != "pdf"):
            raise ValueError("PyMuPDF is linked to an unexpected extra")
        checks.append({"name": "optional_pdf_dependency_boundary", "status": "pass"})

    with tarfile.open(sdist_path, "r:gz") as archive:
        matches = [
            member for member in archive.getmembers()
            if member.isfile() and member.name.endswith("/LICENSE")
        ]
        entry = _require_single(matches, "sdist LICENSE")
        stream = archive.extractfile(entry)
        if stream is None:
            raise ValueError("Could not read sdist LICENSE")
        if hashlib.sha256(stream.read()).hexdigest() != expected_hash:
            raise ValueError("Source distribution LICENSE differs from repository")
    checks.append({"name": "sdist_license_text", "status": "pass"})

    return {
        "schema_version": "1.0",
        "package": "gakufulayer",
        "version": version,
        "wheel": str(wheel_path),
        "sdist": str(sdist_path),
        "source_license_sha256": expected_hash,
        "unconditional_dependencies": sorted(core),
        "optional_dependencies": {key: sorted(vals) for key, vals in sorted(extras.items())},
        "checks": checks,
        "packaging_status": "pass",
        "release_cleared": False,
        "limits": "Packaging smoke check only; all legal/release approvals remain external.",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wheel", required=True)
    parser.add_argument("--sdist", required=True)
    parser.add_argument("--source-license", required=True)
    parser.add_argument("--report", required=True)
    args = parser.parse_args(argv)
    report = check_distributions(args.wheel, args.sdist, args.source_license)
    dest = Path(args.report)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "packaging_status": report["packaging_status"],
        "release_cleared": False,
        "version": report["version"],
        "checks": len(report["checks"]),
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
