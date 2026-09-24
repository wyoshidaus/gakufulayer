"""Core multilingual lyric data structures."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

ReviewStatus = Literal["untranslated", "machine_draft", "needs_review", "reviewed"]


@dataclass(frozen=True)
class TranslationRecord:
    language: str
    text: str
    status: ReviewStatus = "needs_review"
    provider: str | None = None
    reviewer: str | None = None


@dataclass(frozen=True)
class PronunciationRecord:
    language: str
    text: str
    system: str = "IPA"


@dataclass
class LyricSegment:
    segment_id: str
    source_text: str
    source_language: str
    source_page: int
    translations: dict[str, TranslationRecord] = field(default_factory=dict)
    pronunciation: PronunciationRecord | None = None

    def add_translation(self, record: TranslationRecord) -> None:
        if record.language == self.source_language:
            raise ValueError("translation language must differ from source language")
        self.translations[record.language] = record

    def to_dict(self) -> dict:
        return {
            "segment_id": self.segment_id,
            "source_text": self.source_text,
            "source_language": self.source_language,
            "source_page": self.source_page,
            "translations": {
                lang: {
                    "text": record.text,
                    "status": record.status,
                    "provider": record.provider,
                    "reviewer": record.reviewer,
                }
                for lang, record in self.translations.items()
            },
            "pronunciation": (
                {
                    "language": self.pronunciation.language,
                    "system": self.pronunciation.system,
                    "text": self.pronunciation.text,
                }
                if self.pronunciation
                else None
            ),
        }
