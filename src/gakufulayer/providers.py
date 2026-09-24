"""Provider-neutral translation interface.

GakufuLayer's core does not depend on a specific translation API.
Adapters convert provider output into Translation records.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, Sequence

from gakufulayer.annotations import Translation
from gakufulayer.languages import normalize_language_tag


@dataclass(frozen=True)
class TranslationRequest:
    segment_id: str
    text: str
    source_language: str
    target_language: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "source_language", normalize_language_tag(self.source_language)
        )
        object.__setattr__(
            self, "target_language", normalize_language_tag(self.target_language)
        )
        if self.source_language == self.target_language:
            raise ValueError("source and target languages must differ")
        if not self.segment_id.strip():
            raise ValueError("segment_id must not be empty")
        if not self.text.strip():
            raise ValueError("text must not be empty")


class TranslationProvider(Protocol):
    """Minimal adapter contract for machine or local translation providers."""

    name: str

    def translate(self, requests: Sequence[TranslationRequest]) -> list[Translation]:
        """Return translations in the same order as requests."""
        ...


class ReviewedTextProvider:
    """Offline adapter for human-reviewed text supplied by the caller."""

    name = "reviewed-text"

    def __init__(self, translations: dict[tuple[str, str], tuple[str, str]]) -> None:
        self._translations = translations

    def translate(self, requests: Sequence[TranslationRequest]) -> list[Translation]:
        results: list[Translation] = []
        for request in requests:
            key = (request.segment_id, request.target_language)
            if key not in self._translations:
                raise KeyError(
                    f"No reviewed translation for segment {request.segment_id!r} "
                    f"and target {request.target_language!r}"
                )
            text, reviewer = self._translations[key]
            results.append(
                Translation(
                    language=request.target_language,
                    text=text,
                    status="reviewed",
                    provider=self.name,
                    reviewer=reviewer,
                )
            )
        return results
