import pytest

from gakufulayer.policies import (
    JAPANESE_POLICY,
    TargetLanguagePolicy,
    build_translation_brief,
    get_builtin_policy,
)


def test_japanese_policy_ports_vsoper_target_rules():
    assert JAPANESE_POLICY.language == "ja"
    assert JAPANESE_POLICY.one_line_preferred is True
    assert "Noto Serif" in JAPANESE_POLICY.font_family_hint
    assert JAPANESE_POLICY.overlay_color_hint == "royal blue"


def test_builtin_policy_lookup_is_explicit():
    assert get_builtin_policy("JA") is JAPANESE_POLICY
    assert get_builtin_policy("en") is None


def test_translation_brief_separates_source_and_target():
    brief = build_translation_brief(
        source_language="de",
        target_policy=JAPANESE_POLICY,
        work_context="Opera scene",
    )
    assert brief["source_language"] == "de"
    assert brief["target_language"] == "ja"
    assert brief["work_context"] == "Opera scene"
    assert brief["guidance"]


def test_same_source_and_target_rejected():
    with pytest.raises(ValueError):
        build_translation_brief(source_language="ja", target_policy=JAPANESE_POLICY)


def test_rtl_policy_can_be_added_without_changing_core():
    policy = TargetLanguagePolicy(
        language="ar",
        translation_guidance=("Preserve dramatic meaning.",),
        text_direction="rtl",
    )
    assert policy.language == "ar"
    assert policy.text_direction == "rtl"
