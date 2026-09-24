# VSOPER migration audit

## Sources reviewed

The migration review used the owner's current VSOPER specification in Google Drive and the existing private Vocal Score Engine control repository. No score PDF, OCR dump, translation output, font file, or other private/binary work product is copied into GakufuLayer.

## What VSOPER actually contains

VSOPER defines a Japanese-focused opera workflow. Its reusable design ideas include:

- immutable original score pages;
- additive Unicode text overlays rather than routine rasterization or glyph outlines;
- opera-aware role/staff mapping;
- translation from the actual sung score text;
- semantic batching before placement;
- dirty-page rendering;
- page/small-unit checkpoints and resumable state;
- local validation states that can be reused when overlay identity is unchanged;
- Japanese target guidance for concise singer-oriented translation;
- Japanese typography preferences such as Noto Serif CJK JP/Noto Serif JP, one-line placement where practical, and a royal-blue overlay.

The existing control repository also contains a generic translation skill/schema and a PyMuPDF overlay renderer. The translation skill is semantic guidance, not a deterministic Japanese translation implementation.

## Key migration conclusion

There is **no standalone Japanese translation algorithm to copy** from VSOPER. Japanese behavior is primarily policy/specification. GakufuLayer therefore ports it as a target-language policy while keeping translation providers independent.

This distinction matters for multilingual design:

~~~text
source lyric model
        |
translation provider / reviewed text
        |
target-language policy
        |
layout + overlay renderer
~~~

Japanese is the first built-in policy. Other languages can add their own reviewed guidance, fonts, line-breaking behavior, and text direction without changing the shared source-lyric model.

## What is not migrated

- Rosenkavalier or other score PDFs;
- OCR or source-lock data;
- committed Japanese translations from production jobs;
- font binaries;
- private Drive checkpoints;
- any code or asset whose licensing/provenance has not been established.

## Next migration step

Reimplement the reusable overlay architecture inside GakufuLayer under its Apache-2.0 codebase. The renderer should accept generic target-language layout records rather than Japanese-specific fields and should preserve the source PDF as additive content.
