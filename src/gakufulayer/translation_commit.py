"""Validate and atomically commit translation-unit output.

Adapted from the VSOPER transaction pattern, but target-language agnostic.
The module validates line-oriented "segment_id|translation" output and never
performs translation itself.
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any

from gakufulayer.languages import normalize_language_tag


def parse_ready(path: Path) -> list[dict[str, str]]:
    groups: list[dict[str, str]] = []
    seen: set[str] = set()
    for line_no, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not raw.strip():
            continue
        parts = raw.split("|", 2)
        if len(parts) != 3:
            raise ValueError(
                f"Malformed ready line {line_no}: expected ID|speaker|source"
            )
        segment_id, speaker, source_text = (part.strip() for part in parts)
        if not segment_id or not source_text:
            raise ValueError(
                f"Malformed ready line {line_no}: empty id/source"
            )
        if segment_id in seen:
            raise ValueError(f"Duplicate expected segment id: {segment_id}")
        seen.add(segment_id)
        groups.append(
            {
                "source_ref": segment_id,
                "speaker": "" if speaker == "?" else speaker,
                "source_text": source_text,
            }
        )
    if not groups:
        raise ValueError("Translation unit contains no groups")
    return groups


def parse_translation_output(text: str) -> tuple[dict[str, str], dict[str, Any]]:
    values: dict[str, str] = {}
    duplicates: list[str] = []
    malformed: list[dict[str, Any]] = []
    empty: list[str] = []
    parsed_order: list[str] = []

    for line_no, raw in enumerate(text.splitlines(), start=1):
        line = raw.strip()
        if not line:
            continue
        if "|" not in line:
            malformed.append({"line": line_no, "text": raw})
            continue
        segment_id, target = line.split("|", 1)
        segment_id = segment_id.strip()
        target = target.strip()
        if not segment_id:
            malformed.append({"line": line_no, "text": raw})
            continue
        if segment_id in values:
            duplicates.append(segment_id)
            continue
        values[segment_id] = target
        parsed_order.append(segment_id)
        if not target:
            empty.append(segment_id)

    return values, {
        "duplicates": duplicates,
        "malformed": malformed,
        "empty": empty,
        "parsed_order": parsed_order,
    }


def validate_translation(
    expected: list[dict[str, str]],
    output_text: str,
) -> tuple[dict[str, Any], list[dict[str, str]]]:
    values, parse_report = parse_translation_output(output_text)
    expected_ids = [item["source_ref"] for item in expected]
    expected_set = set(expected_ids)
    actual_set = set(values)

    missing = [item for item in expected_ids if item not in actual_set]
    unexpected = sorted(actual_set - expected_set)
    duplicates = sorted(set(parse_report["duplicates"]))
    empty = [
        item for item in expected_ids if item in parse_report["empty"]
    ]

    completed_ids = [
        item
        for item in expected_ids
        if item in values and item not in empty and item not in duplicates
    ]
    expected_index = {item["source_ref"]: item for item in expected}
    groups = [
        {
            "source_ref": item,
            "speaker": expected_index[item]["speaker"],
            "source_text": expected_index[item]["source_text"],
            "target_text": values[item],
        }
        for item in completed_ids
    ]

    valid = not (
        missing
        or unexpected
        or duplicates
        or empty
        or parse_report["malformed"]
    )
    report = {
        "status": "passed" if valid else "failed",
        "expected_count": len(expected_ids),
        "completed_count": len(completed_ids),
        "completed_ids": completed_ids,
        "missing_ids": missing,
        "unexpected_ids": unexpected,
        "duplicate_ids": duplicates,
        "empty_ids": empty,
        "malformed_lines": parse_report["malformed"],
        "output_order_matches_source": (
            [x for x in parse_report["parsed_order"] if x in expected_set]
            == [x for x in expected_ids if x in actual_set]
        ),
    }
    return report, groups


def _atomic_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=str(path.parent),
        text=True,
    )
    tmp = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, path)
    finally:
        if tmp.exists():
            tmp.unlink()


def commit_translation(
    ready_path: Path,
    output_path: Path,
    passed_path: Path,
    *,
    source_language: str,
    target_language: str,
    overwrite: bool = False,
) -> dict[str, Any]:
    """Validate a unit and create an immutable passed marker on success."""
    source = normalize_language_tag(source_language)
    target = normalize_language_tag(target_language)
    if source == target:
        raise ValueError("source and target languages must differ")

    unit_id = ready_path.name.split(".", 1)[0]
    if passed_path.exists() and not overwrite:
        return {
            "status": "already_committed",
            "unit": unit_id,
            "passed": str(passed_path),
        }

    expected = parse_ready(ready_path)
    report, groups = validate_translation(
        expected, output_path.read_text(encoding="utf-8")
    )
    failed_path = passed_path.parent / f"{unit_id}.{target}.failed.json"

    base = {
        "unit": unit_id,
        "source_language": source,
        "target_language": target,
        "source": str(ready_path),
        "translation_output": str(output_path),
        "groups": groups,
        **report,
    }

    if report["status"] != "passed":
        _atomic_json(failed_path, base)
        return {**report, "unit": unit_id, "failed": str(failed_path)}

    payload = {
        "status": "passed",
        "unit": unit_id,
        "source_language": source,
        "target_language": target,
        "group_count": len(groups),
        "groups": groups,
    }
    _atomic_json(passed_path, payload)
    if failed_path.exists():
        failed_path.unlink()

    return {
        **report,
        "unit": unit_id,
        "passed": str(passed_path),
    }
