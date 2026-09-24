import pytest

from gakufulayer.providers import ReviewedTextProvider, TranslationRequest


def test_reviewed_text_provider_is_language_independent():
    provider = ReviewedTextProvider(
        {
            ("s1", "ja"): ("こんばんは", "reviewer-ja"),
            ("s1", "en"): ("Good evening", "reviewer-en"),
        }
    )
    requests = [
        TranslationRequest("s1", "Guten Abend", "de", "ja"),
        TranslationRequest("s1", "Guten Abend", "de", "en"),
    ]
    result = provider.translate(requests)
    assert [item.language for item in result] == ["ja", "en"]
    assert all(item.status == "reviewed" for item in result)
    assert [item.reviewer for item in result] == ["reviewer-ja", "reviewer-en"]


def test_request_normalizes_language_tags():
    request = TranslationRequest("s1", "Olá", "PT-br", "EN")
    assert request.source_language == "pt-BR"
    assert request.target_language == "en"


def test_same_source_and_target_are_rejected():
    with pytest.raises(ValueError, match="must differ"):
        TranslationRequest("s1", "bonjour", "fr", "FR")


def test_missing_reviewed_translation_fails_explicitly():
    provider = ReviewedTextProvider({})
    with pytest.raises(KeyError):
        provider.translate([TranslationRequest("s1", "ciao", "it", "ja")])
