# VSOPER migration audit

This document records what was found in the existing VSOPER implementation before migration into GakufuLayer.

## Findings

VSOPER does not contain a standalone Japanese machine-translation model or an API client that can simply be copied. Its translation path is split into:

1. instructions for ChatGPT to translate aligned sung text;
2. a line-oriented Translation Unit format;
3. validation and atomic commit of generated translations;
4. compilation into a translation schema whose default target language is Japanese;
5. Japanese-specific font/render checks later in the PDF pipeline.

The reusable transaction logic was found in `scripts/vsoper_translation_commit.py`. It checks missing, duplicate, unexpected and empty IDs; recovers complete lines before a truncated tail; creates a passed marker only after complete validation; and leaves committed results immutable unless overwrite is explicit.

## Migration decision

GakufuLayer ports the transaction semantics but removes Japanese as an implicit target. Every committed unit records explicit normalized `source_language` and `target_language` values. The same validation path is tested with Japanese and English output.

The original VSOPER prompt/skill is treated as behavioral documentation rather than a translation engine. Actual translation providers belong behind GakufuLayer's provider-neutral interface.

## Not migrated yet

- VSOPER PDF coordinate extraction and score-structure heuristics;
- Japanese-specific compile/render defaults;
- Japanese font fallback and extraction QC;
- Rosenkavalier fixtures tied to the historical VSOPER development work;
- any score PDF, libretto, translated text, or other third-party asset whose redistribution rights are not established.

These parts require separate audit and, where appropriate, language-neutral redesign.
