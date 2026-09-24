"""Language selection tests; no real translations are generated yet."""

import pytest

from gakufulayer.languages import configure_languages, normalize_language_tag


@pytest.mark.parametrize(
    "raw,canonical",
    [
        ("DE", "de"),
        (" ja ", "ja"),
        ("pt-br", "pt-BR"),
        ("zh-hans", "zh-Hans"),
        ("zh-hant-tw", "zh-Hant-TW"),
        ("es-419", "es-419"),
    ],
)
def test_normalize_language_tag(raw, canonical):
    assert normalize_language_tag(raw) == canonical


@pytest.mark.parametrize("invalid", ["", "english", "d", "ja_XX", "de--DE", "de-x-private"])
def test_reject_unsupported_or_invalid_tags(invalid):
    with pytest.raises(ValueError):
        normalize_language_tag(invalid)


def test_multilingual_targets_are_ordered_and_deduplicated():
    selection = configure_languages("DE", ["ja", "en", "JA", "fr"])
    assert selection.to_manifest() == {"source": "de", "targets": ["ja", "en", "fr"]}


def test_targets_require_source():
    with pytest.raises(ValueError, match="source-language"):
        configure_languages(None, ["ja"])


def test_source_only():
    assert configure_languages("fr").to_manifest() == {"source": "fr", "targets": []}
