import pytest

from gakufulayer.annotations import LyricSegment, Pronunciation, Translation


def test_segment_supports_multiple_independent_translations():
    segment = LyricSegment("seg-1", "Guten Abend", "DE", 12)
    segment.add_translation(Translation("ja", "こんばんは", reviewer="A", status="reviewed"))
    segment.add_translation(Translation("en", "Good evening", provider="example"))
    assert list(segment.to_dict()["translations"]) == ["ja", "en"]
    assert segment.to_dict()["source_language"] == "de"


def test_pronunciation_belongs_to_source_language():
    segment = LyricSegment("seg-1", "bonjour", "fr", 1)
    segment.set_pronunciation(Pronunciation("FR", "bɔ̃.ʒuʁ"))
    assert segment.to_dict()["pronunciation"]["language"] == "fr"


def test_translation_cannot_duplicate_source_language():
    segment = LyricSegment("seg-1", "bonjour", "fr", 1)
    with pytest.raises(ValueError):
        segment.add_translation(Translation("fr", "bonjour"))


def test_reviewed_translation_requires_reviewer():
    with pytest.raises(ValueError, match="reviewer"):
        Translation("ja", "こんばんは", status="reviewed")


def test_pronunciation_language_must_match_source():
    segment = LyricSegment("seg-1", "bonjour", "fr", 1)
    with pytest.raises(ValueError, match="match source"):
        segment.set_pronunciation(Pronunciation("de", "bɔ̃.ʒuʁ"))
