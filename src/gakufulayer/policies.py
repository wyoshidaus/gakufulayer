"""Target-language policies kept separate from translation providers."""

from __future__ import annotations

from dataclasses import dataclass

from gakufulayer.languages import normalize_language_tag


@dataclass(frozen=True)
class TargetLanguagePolicy:
    language: str
    translation_guidance: tuple[str, ...]
    one_line_preferred: bool = False
    font_family_hint: str | None = None
    font_weight_hint: str | None = None
    overlay_color_hint: str | None = None
    text_direction: str = "ltr"

    def __post_init__(self) -> None:
        object.__setattr__(self, "language", normalize_language_tag(self.language))
        if self.text_direction not in {"ltr", "rtl"}:
            raise ValueError("text_direction must be 'ltr' or 'rtl'")


JAPANESE_POLICY = TargetLanguagePolicy(
    language="ja",
    translation_guidance=(
        "Be concise, natural, literary, and useful to a singer.",
        "Preserve meaning, grammar, person, tense, imagery, dramatic relationship, register, and historical semantics.",
        "Map one meaningful or musical sung phrase to one concise target phrase when practical.",
        "Translate the actual sung score text; stage directions are context unless clearly sung.",
        "Keep terminology and character voice consistent across a semantic block.",
    ),
    one_line_preferred=True,
    font_family_hint="Noto Serif CJK JP / Noto Serif JP",
    font_weight_hint="SemiBold/Bold where readable",
    overlay_color_hint="royal blue",
)


def get_builtin_policy(language: str) -> TargetLanguagePolicy | None:
    """Return a reviewed built-in target policy when one exists."""
    normalized = normalize_language_tag(language)
    if normalized == "ja":
        return JAPANESE_POLICY
    return None


def build_translation_brief(
    *,
    source_language: str,
    target_policy: TargetLanguagePolicy,
    work_context: str | None = None,
) -> dict:
    """Build provider-neutral semantic instructions for a target language."""
    source = normalize_language_tag(source_language)
    if source == target_policy.language:
        raise ValueError("source and target languages must differ")
    return {
        "source_language": source,
        "target_language": target_policy.language,
        "work_context": work_context,
        "guidance": list(target_policy.translation_guidance),
        "layout_preferences": {
            "one_line_preferred": target_policy.one_line_preferred,
            "font_family_hint": target_policy.font_family_hint,
            "font_weight_hint": target_policy.font_weight_hint,
            "overlay_color_hint": target_policy.overlay_color_hint,
            "text_direction": target_policy.text_direction,
        },
    }
