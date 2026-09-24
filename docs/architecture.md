# Architecture

GakufuLayer is designed as a multilingual, page-block pipeline for preparing long vocal scores without reprocessing completed blocks.

## Implemented

The preprocess command takes a PDF, optional inclusive 1-based page range, block size, optional source language and zero or more target languages. It uses pypdf to write page blocks and a JSON manifest. Language fields declare intended output languages. A separate, provider-neutral translation interface accepts reviewed text; VSOPER-derived transaction checks validate/commit external translation output. The renderer consumes pre-reviewed, pre-positioned text in a JSON document, creates a separate PDF for every target language and optionally a combined PDF with mutually exclusive OCGs. The score page contents are not rasterized. No machine translation, IPA generation, OCR or source-page image hashing occurs.

## Planned stages — not implemented

1. Extract lyric text and align its fragments to source pages and coordinates.
2. Create source-language lyric segments, with stable IDs independent of translations.
3. Import or generate target-language translations through replaceable providers; preserve provider and reviewer provenance.
4. Generate separate source-language IPA annotations when appropriate.
5. Generate score-aware, collision-checked rectangles for each target language. Current HTML shaping/OCG rendering only consumes supplied rectangles; Japanese and Latin tests run, Arabic requires an explicit font.
6. Validate per-block output, resume unfinished blocks and assemble PDFs.

See the multilingual design document for language-tag rules and future data structures.

The code license and score/lyric/translation reuse rights are separate matters.
