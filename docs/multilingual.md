# Multilingual design

## Requirements

- Do not hard-code Japanese as the target language.
- Accept one source language and zero or more target languages.
- Keep source lyric segments separate from every translation and pronunciation annotation.
- Allow each target to have distinct text length, typographic rules and PDF annotation layer.
- Preserve the original score; avoid unnecessary page rasterization.
- Track translation and review status per source segment and target language.
- Permit human-reviewed text imports and future provider adapters; do not tie the pipeline to a paid API.

## Prototype language metadata

The first milestone records language settings in manifest.json:

~~~json
{
  "schema_version": "1.1",
  "languages": {"source": "de", "targets": ["ja", "en"]}
}
~~~

Language tags currently support a limited subset of BCP 47: two- or three-letter primary language, optional four-letter script, and optional two-letter or three-digit region. Examples: de, ja, fr, pt-BR, zh-Hans, zh-Hant-TW, es-419. Variant and extension subtags require a future enhancement. Normalization is purely syntactic and does not guarantee that a translation provider, font or IPA model supports the selected language.

## Proposed annotation record (not yet implemented)

~~~json
{
  "segment_id": "source-0001",
  "source_text": "...",
  "source_language": "de",
  "source_page": 1,
  "translations": {
    "ja": {"text": "...", "status": "needs_review"},
    "en": {"text": "...", "status": "needs_review"}
  },
  "pronunciation": {"system": "IPA", "language": "de", "text": "..."}
}
~~~

Rendering must not assume that every language has the same line count or reading direction. Initial releases should prioritize a few tested language pairs; broad tag support does not imply translation quality for every pair. Language coverage and QA results should be documented explicitly.
