"""Inventory installed Python distributions and capture package license evidence.

The output is an environment snapshot for release review, not a lockfile,
SPDX certification, or a determination of legal compatibility. This script
uses only the Python standard library so it runs in the core-only CI venv.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata as metadata
import json
import platform
import re
from pathlib import Path, PurePosixPath
from typing import Any, Iterable

_MAX_NOTICE_BYTES = 2_000_000
_NOTICE_NAME = re.compile(
    r"^(?:LICENSE|LICENCE|COPYING|NOTICE|THIRD[-_]?PARTY[-_]?NOTICES?)"
    r"(?:$|[-_.].*)",
    re.IGNORECASE,
)


def canonical_name(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).casefold()


def _license_markers(dist: metadata.Distribution) -> list[str]:
    expression = dist.metadata.get("License-Expression")
    if expression and expression.strip():
        return [expression.strip()]
    classifiers = dist.metadata.get_all("Classifier", [])
    license_classes = sorted(c for c in classifiers if c.startswith("License ::"))
    if license_classes:
        return license_classes
    legacy = (dist.metadata.get("License") or "").strip()
    if legacy and len(legacy) <= 160 and "\n" not in legacy:
        return [legacy]
    return ["unknown: review package metadata and bundled LICENSE files"]


def _notice_candidates(dist: metadata.Distribution) -> list[str]:
    named = {
        str(name).replace("\\", "/")
        for name in (dist.metadata.get_all("License-File", []) or [])
    }
    paths: set[str] = set()
    for item in dist.files or ():
        rel = str(item).replace("\\", "/")
        if PurePosixPath(rel).is_absolute() or ".." in PurePosixPath(rel).parts:
            continue
        file_name = PurePosixPath(rel).name
        # Some wheels keep license texts in <dist-info>/licenses/, whereas
        # older ones put LICENSE or COPYING directly under <dist-info>.
        if _NOTICE_NAME.match(file_name) or any(
            rel == explicit or rel.endswith("/" + explicit) for explicit in named
        ):
            paths.add(rel)
    return sorted(paths)


def _evidence(
    dist: metadata.Distribution,
    *,
    notice_dir: Path | None,
    safe_package: str,
    safe_version: str,
) -> tuple[list[dict[str, Any]], list[str]]:
    evidence: list[dict[str, Any]] = []
    warnings: list[str] = []
    for idx, relative in enumerate(_notice_candidates(dist)):
        try:
            path = Path(dist.locate_file(relative))
            size = path.stat().st_size
            if not path.is_file() or size > _MAX_NOTICE_BYTES:
                warnings.append(f"license_file_missing_or_too_large:{relative}")
                continue
            data = path.read_bytes()
        except (OSError, TypeError, ValueError) as exc:
            warnings.append(f"license_file_unreadable:{relative}:{type(exc).__name__}")
            continue
        item: dict[str, Any] = {
            "distribution_path": relative,
            "size_bytes": len(data),
            "sha256": hashlib.sha256(data).hexdigest(),
        }
        if notice_dir is not None:
            name = re.sub(r"[^a-zA-Z0-9._-]+", "_", PurePosixPath(relative).name)
            output = notice_dir / f"{safe_package}-{safe_version}" / f"{idx:03d}-{name}"
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_bytes(data)
            item["evidence_path"] = output.relative_to(notice_dir).as_posix()
        evidence.append(item)
    return evidence, warnings


def collect_inventory(
    distributions: Iterable[metadata.Distribution] | None = None,
    *,
    mode: str = "unclassified",
    notice_dir: str | Path | None = None,
) -> dict[str, Any]:
    if mode not in {"core", "full", "unclassified"}:
        raise ValueError("mode must be core, full or unclassified")
    evidence_dir = Path(notice_dir) if notice_dir is not None else None
    if evidence_dir is not None:
        evidence_dir.mkdir(parents=True, exist_ok=True)

    # Editable installs may be discoverable more than once. Inventory unique
    # normalized package+version identities and retain the richer evidence.
    by_identity: dict[tuple[str, str], dict[str, Any]] = {}
    for dist in distributions if distributions is not None else metadata.distributions():
        display_name = (dist.metadata.get("Name") or "unknown").strip()
        version = str(dist.version)
        key = (canonical_name(display_name), version)
        markers = _license_markers(dist)
        safe_name = re.sub(r"[^a-z0-9._-]+", "_", key[0])
        safe_version = re.sub(r"[^a-zA-Z0-9._-]+", "_", version)
        license_files, problems = _evidence(
            dist, notice_dir=evidence_dir, safe_package=safe_name,
            safe_version=safe_version,
        )
        requires = sorted(str(r) for r in (dist.requires or ()))
        entry = {
            "name": display_name,
            "normalized_name": key[0],
            "version": version,
            "license_markers": markers,
            "license_files": license_files,
            "requires_dist": requires,
            "evidence_warnings": problems,
        }
        if key not in by_identity:
            by_identity[key] = entry
        else:
            current = by_identity[key]
            for field in ("license_files", "requires_dist", "evidence_warnings"):
                unique = {json.dumps(x, sort_keys=True): x
                          for x in current[field] + entry[field]}
                current[field] = sorted(unique.values(), key=lambda x: str(x))
            if current["license_markers"][0].startswith("unknown:") and (
                not markers[0].startswith("unknown:")
            ):
                current["license_markers"] = markers

    packages = [by_identity[key] for key in sorted(by_identity)]
    for package in packages:
        # Editable installs can yield both an ordinary dist-info record and
        # a synthetic editable metadata record. If the same license file was
        # successfully read from one, do not retain a stale "unreadable"
        # warning from its duplicate.
        successful = {item["distribution_path"] for item in package["license_files"]}
        remaining = []
        for warning in package["evidence_warnings"]:
            parts = warning.split(":", 2)
            if (
                len(parts) >= 2
                and parts[0] in {"license_file_unreadable", "license_file_missing_or_too_large"}
                and parts[1] in successful
            ):
                continue
            remaining.append(warning)
        package["evidence_warnings"] = remaining
    review: list[dict[str, str]] = []
    names = {p["normalized_name"] for p in packages}
    for package in packages:
        pkg = package["normalized_name"]
        if package["license_markers"][0].startswith("unknown:"):
            review.append({"package": pkg, "reason": "license_expression_unknown"})
        if not package["license_files"]:
            review.append({"package": pkg, "reason": "bundled_license_text_not_found"})
        if package["evidence_warnings"]:
            review.append({"package": pkg, "reason": "license_evidence_incomplete"})
        if pkg == "pymupdf":
            review.append({
                "package": pkg,
                "reason": "AGPLv3_or_commercial_licensing_route_requires_manual_decision",
            })

    environment_errors: list[str] = []
    if mode in {"core", "full"} and "pypdf" not in names:
        environment_errors.append("pypdf_missing")
    if mode == "core" and "pymupdf" in names:
        environment_errors.append("PyMuPDF_must_not_be_in_core_install")
    if mode == "full" and "pymupdf" not in names:
        environment_errors.append("PyMuPDF_missing_from_full_install")
    return {
        "schema_version": "1.1",
        "inventory_type": "Installed snapshot; not pinned or legally approved",
        "mode": mode,
        "python_version": platform.python_version(),
        "packages": packages,
        "review_required": review,
        "environment_errors": environment_errors,
        "release_cleared": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=["core", "full", "unclassified"],
                        default="unclassified")
    parser.add_argument("--output", help="JSON output path (stdout if omitted)")
    parser.add_argument("--notice-dir", help="Copy discovered license files here for review")
    args = parser.parse_args(argv)
    result = collect_inventory(mode=args.mode, notice_dir=args.notice_dir)
    payload = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        target = Path(args.output)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(payload, encoding="utf-8")
        print(json.dumps({
            "mode": args.mode, "packages": len(result["packages"]),
            "review_required": len(result["review_required"]),
            "environment_errors": result["environment_errors"],
            "output": str(target),
        }))
    else:
        print(payload, end="")
    return 1 if result["environment_errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
