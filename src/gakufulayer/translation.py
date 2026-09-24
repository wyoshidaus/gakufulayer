"""Translation adapter interfaces.

Adapters transform source lyric text into a target-language draft. They do not
write PDFs and they do not mark machine output as human-reviewed.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from gakufulayer.languages import normalize_language_tag
from gakufulayer.models import TranslationRecord


@dataclass(frozen=True)
class TranslationRequest:
    text: str
    source_language: str
    target_language: str

    def normalized(self) -> "TranslationRequest":
        source = normalize_language_tag(self.source_language)
        target = normalize_language_tag(self.target_language)
        if source == target:
            raise ValueError("source and target language must differ")
        return TranslationRequest(
            text=self.text,
            source_language=source,
            target_language=target,
        )


class TranslationProvider(Protocol):
    """Minimal interface for replaceable translation providers."""

    name: str

    def translate(self, request: TranslationRequest) -> TranslationRecord:
        """Return a draft translation. Implementations must not claim review."""


class EchoTranslationProvider:
    """Testing provider that echoes text; not a real translator."""

    name = "echo-test"

    def translate(self, request: TranslationRequest) -> TranslationRecord:
        normalized = request.normalized()
        return TranslationRecord(
            language=normalized.target_language,
            text=normalized.text,
            status="machine_draft",
            provider=self.name,
        )
