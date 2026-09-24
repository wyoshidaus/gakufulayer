"""Language-independent lyric records and curated translation bundles.

This module deliberately does not extract lyrics from scores, call translation
services, generate IPA, or alter PDFs. It prepares auditable, per-language JSON
bundles that future rendering stages can consume.
"""

from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from gakufulayer.languages import configure_languages, normalize_language_tag

_SCHEMA_VERSION = "1.0"
_SEGMENT_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,79}$")
_VALID_STATUSES = frozenset({"draft", "reviewed"})


@dataclass(frozen=True)
class LyricSegment:
    """Source lyrics with optional PDF coordinates (points, bottom-left origin)."""

    id: str
    text: str
    page: int
    bbox: tuple[float, float, float, float] | None = None

    def to_dict(self) -> dict:
        result = {"id": self.id, "page": self.page, "text": self.text}
        if self.bbox is not None:
            result["bbox"] = list(self.bbox)
        return result


@dataclass(frozen=True)
class TranslationEntry:
    segment_id: str
    language: str
    text: str
    status: str


class TranslationProvider(Protocol):
    """Read-only interface that future translation adapters can implement."""

    def lookup(self, segment_id: str, target_language: str) -> TranslationEntry | None:
        ...


@dataclass
class CuratedJSONProvider:
    """Human-supplied translation data, including explicitly marked drafts."""

    translations: dict[tuple[str, str], TranslationEntry]

    def lookup(self, segment_id: str, target_language: str) -> TranslationEntry | None:
        return self.translations.get((segment_id, target_language))


def _read_json_object(path: str | Path) -> dict:
    with Path(path).open(encoding="utf-8") as stream:
        data = json.load(stream)
    if not isinstance(data, dict):
        raise ValueError(f"{path}: JSON root must be an object")
    if data.get("schema_version") != _SCHEMA_VERSION:
        raise ValueError(f"{path}: expected schema_version {_SCHEMA_VERSION!r}")
    return data


def _nonempty_string(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a nonempty string")
    return value


def _bbox(value: object, segment_id: str) -> tuple[float, float, float, float]:
    if not isinstance(value, list) or len(value) != 4:
        raise ValueError(f"{segment_id}: bbox must be [left, bottom, right, top]")
    if any(isinstance(n, bool) or not isinstance(n, (float, int)) for n in value):
        raise ValueError(f"{segment_id}: bbox coordinates must be numbers")
    coords = tuple(float(n) for n in value)
    x0, y0, x1, y1 = coords
    if not all(math.isfinite(n) and n >= 0 for n in coords) or x1 <= x0 or y1 <= y0:
        raise ValueError(f"{segment_id}: bbox must be finite and have positive area")
    return coords


def load_segments(path: str | Path) -> tuple[str, tuple[LyricSegment, ...]]:
    """Read manually prepared source segments, in their declared score order."""
    data = _read_json_object(path)
    source_language = normalize_language_tag(
        _nonempty_string(data.get("source_language"), "source_language")
    )
    records = data.get("segments")
    if not isinstance(records, list) or not records:
        raise ValueError("segments must be a nonempty list")
    segments: list[LyricSegment] = []
    used_ids: set[str] = set()
    for index, item in enumerate(records):
        if not isinstance(item, dict):
            raise ValueError(f"segment {index}: must be an object")
        ident = _nonempty_string(item.get("id"), f"segment {index} id")
        if not _SEGMENT_ID.fullmatch(ident):
            raise ValueError(f"segment {index}: invalid id {ident!r}")
        if ident in used_ids:
            raise ValueError(f"duplicate source segment id {ident!r}")
        used_ids.add(ident)
        text = _nonempty_string(item.get("text"), f"{ident} text")
        page = item.get("page")
        if isinstance(page, bool) or not isinstance(page, int) or page < 1:
            raise ValueError(f"{ident}: page must be a positive integer")
        bbox = _bbox(item["bbox"], ident) if "bbox" in item else None
        segments.append(LyricSegment(id=ident, text=text, page=page, bbox=bbox))
    return source_language, tuple(segments)


def load_curated_translations(
    path: str | Path, known_segment_ids: set[str]
) -> CuratedJSONProvider:
    """Validate a reviewed/draft text catalog; never silently accept unknown IDs."""
    data = _read_json_object(path)
    items = data.get("translations")
    if not isinstance(items, list):
        raise ValueError("translations must be a list")
    entries: dict[tuple[str, str], TranslationEntry] = {}
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            raise ValueError(f"translation {index}: must be an object")
        segment_id = _nonempty_string(item.get("segment_id"), f"translation {index} segment_id")
        if segment_id not in known_segment_ids:
            raise ValueError(f"translation {index}: unknown source segment {segment_id!r}")
        language = normalize_language_tag(
            _nonempty_string(item.get("language"), f"translation {index} language")
        )
        text = _nonempty_string(item.get("text"), f"translation {index} text")
        status = item.get("status")
        if not isinstance(status, str) or status not in _VALID_STATUSES:
            raise ValueError(
                f"translation {index}: status must be 'draft' or 'reviewed'"
            )
        key = (segment_id, language)
        if key in entries:
            raise ValueError(f"duplicate translation for {segment_id!r} in {language!r}")
        entries[key] = TranslationEntry(segment_id, language, text, status)
    return CuratedJSONProvider(entries)


def bundle_annotations(
    segments_json: str | Path,
    translations_json: str | Path,
    output_dir: str | Path,
    target_languages: list[str],
) -> dict[str, dict]:
    """Write a separate JSON bundle per target; missing entries remain explicit."""
    source_language, segments = load_segments(segments_json)
    settings = configure_languages(source_language, target_languages)
    if not settings.targets:
        raise ValueError("at least one target language is required")
    if source_language in settings.targets:
        raise ValueError("target languages must differ from the source language")
    provider: TranslationProvider = load_curated_translations(
        translations_json, {segment.id for segment in segments}
    )
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    bundles: dict[str, dict] = {}
    for language in settings.targets:
        counts = {"reviewed": 0, "draft": 0, "missing": 0}
        records: list[dict] = []
        for segment in segments:
            translation = provider.lookup(segment.id, language)
            entry = {"source": segment.to_dict(), "translation": None}
            if translation is None:
                counts["missing"] += 1
            else:
                counts[translation.status] += 1
                entry["translation"] = {
                    "text": translation.text,
                    "status": translation.status,
                }
            records.append(entry)
        bundle = {
            "schema_version": _SCHEMA_VERSION,
            "source_language": source_language,
            "target_language": language,
            "segments": records,
            "counts": counts,
        }
        (out_dir / f"annotations_{language}.json").write_text(
            json.dumps(bundle, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        bundles[language] = bundle
    return bundles
