"""Language-independent lyric and annotation data models."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Literal

from gakufulayer.languages import normalize_language_tag

ReviewStatus = Literal["machine", "needs_review", "reviewed"]


@dataclass(frozen=True)
class Translation:
    language: str
    text: str
    status: ReviewStatus = "needs_review"
    provider: str | None = None
    reviewer: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "language", normalize_language_tag(self.language))
        if not self.text.strip():
            raise ValueError("translation text must not be empty")
        if self.status == "reviewed" and not self.reviewer:
            raise ValueError("reviewed translations require reviewer metadata")


@dataclass(frozen=True)
class Pronunciation:
    language: str
    text: str
    system: str = "IPA"

    def __post_init__(self) -> None:
        object.__setattr__(self, "language", normalize_language_tag(self.language))
        if not self.text.strip():
            raise ValueError("pronunciation text must not be empty")
        if self.system != "IPA":
            raise ValueError("only IPA is supported in the prototype")


@dataclass
class LyricSegment:
    segment_id: str
    source_text: str
    source_language: str
    source_page: int
    translations: dict[str, Translation] = field(default_factory=dict)
    pronunciation: Pronunciation | None = None

    def __post_init__(self) -> None:
        self.source_language = normalize_language_tag(self.source_language)
        if not self.segment_id.strip():
            raise ValueError("segment_id must not be empty")
        if not self.source_text.strip():
            raise ValueError("source_text must not be empty")
        if self.source_page < 1:
            raise ValueError("source_page must be 1 or greater")

    def add_translation(self, translation: Translation) -> None:
        if translation.language == self.source_language:
            raise ValueError("translation language must differ from source language")
        self.translations[translation.language] = translation

    def set_pronunciation(self, pronunciation: Pronunciation) -> None:
        if pronunciation.language != self.source_language:
            raise ValueError("pronunciation language must match source language")
        self.pronunciation = pronunciation

    def to_dict(self) -> dict:
        return {
            "segment_id": self.segment_id,
            "source_text": self.source_text,
            "source_language": self.source_language,
            "source_page": self.source_page,
            "translations": {
                lang: asdict(value) for lang, value in self.translations.items()
            },
            "pronunciation": asdict(self.pronunciation)
            if self.pronunciation is not None
            else None,
        }
