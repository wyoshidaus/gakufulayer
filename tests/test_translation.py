"""Tests for provider-neutral multilingual translation interfaces."""

import pytest

from gakufulayer.models import LyricSegment, TranslationRecord
from gakufulayer.translation import EchoTranslationProvider, TranslationRequest


def test_translation_request_normalizes_languages():
    request = TranslationRequest("Guten Abend", "DE", "ja").normalized()
    assert request.source_language == "de"
    assert request.target_language == "ja"


def test_translation_request_rejects_same_language():
    with pytest.raises(ValueError):
        TranslationRequest("text", "de", "DE").normalized()


def test_echo_provider_is_explicitly_machine_draft():
    record = EchoTranslationProvider().translate(
        TranslationRequest("Bonjour", "fr", "en")
    )
    assert record.language == "en"
    assert record.text == "Bonjour"
    assert record.status == "machine_draft"
    assert record.provider == "echo-test"
    assert record.reviewer is None


def test_segment_can_hold_multiple_target_languages():
    segment = LyricSegment(
        segment_id="source-0001",
        source_text="Guten Abend",
        source_language="de",
        source_page=1,
    )
    segment.add_translation(
        TranslationRecord(language="ja", text="こんばんは", status="reviewed", reviewer="human")
    )
    segment.add_translation(
        TranslationRecord(language="en", text="Good evening", status="needs_review")
    )

    data = segment.to_dict()
    assert set(data["translations"]) == {"ja", "en"}
    assert data["translations"]["ja"]["status"] == "reviewed"
    assert data["translations"]["en"]["status"] == "needs_review"


def test_segment_rejects_translation_in_source_language():
    segment = LyricSegment("source-0001", "Hallo", "de", 1)
    with pytest.raises(ValueError):
        segment.add_translation(TranslationRecord(language="de", text="Hallo"))
