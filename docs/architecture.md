# Architecture

GakufuLayer is designed as a multilingual, page-block pipeline for preparing long vocal scores without reprocessing completed blocks.

## Implemented

The preprocess command takes a PDF, optional inclusive 1-based page range, block size, optional source language and zero or more target languages. It uses pypdf to write page blocks and a JSON manifest. Language fields declare intended output languages only; no translation or IPA processing occurs. The prototype neither rasterizes notation nor performs OCR or source-page image hashing.

## Planned stages — not implemented

1. Extract lyric text and align its fragments to source pages and coordinates.
2. Create source-language lyric segments, with stable IDs independent of translations.
3. Import or generate target-language translations through replaceable providers; preserve provider and reviewer provenance.
4. Generate separate source-language IPA annotations when appropriate.
5. Layout independent annotation layers for each target language. Select appropriate fonts, line breaks and left-to-right/right-to-left text behavior without altering music notation.
6. Validate per-block output, resume unfinished blocks and assemble PDFs.

See the multilingual design document for language-tag rules and future data structures.

The code license and score/lyric/translation reuse rights are separate matters.
