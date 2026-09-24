"""Language metadata for future multilingual lyric-annotation workflows.

This module validates a deliberately small, documented subset of BCP 47.
It does not translate text or claim to support every possible language tag.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable

_TAG = re.compile(r"^[A-Za-z]{2,3}(?:-[A-Za-z]{4})?(?:-(?:[A-Za-z]{2}|[0-9]{3}))?$")


def normalize_language_tag(tag: str) -> str:
    """Normalize common tags, e.g. de, ja, pt-BR, zh-Hans, zh-Hant-TW.

    Variant and extension subtags are not supported in the prototype.
    """
    cleaned = tag.strip()
    if not _TAG.fullmatch(cleaned):
        raise ValueError(
            f"Invalid language tag {tag!r}. Expected a 2- or 3-letter language "
            "with an optional 4-letter script and 2-letter/3-digit region."
        )
    parts = cleaned.split("-")
    result = [parts[0].lower()]
    for part in parts[1:]:
        result.append(part.title() if len(part) == 4 else part.upper())
    return "-".join(result)


@dataclass(frozen=True)
class LanguageSettings:
    source: str | None
    targets: tuple[str, ...]

    def to_manifest(self) -> dict[str, str | list[str] | None]:
        return {"source": self.source, "targets": list(self.targets)}


def configure_languages(
    source_language: str | None, target_languages: Iterable[str] | None = None
) -> LanguageSettings:
    """Normalize source and target tags, preserving order without duplicates."""
    source = normalize_language_tag(source_language) if source_language else None
    targets = tuple(
        dict.fromkeys(normalize_language_tag(tag) for tag in (target_languages or ()))
    )
    if targets and source is None:
        raise ValueError("--source-language is required when targets are specified")
    return LanguageSettings(source=source, targets=targets)
