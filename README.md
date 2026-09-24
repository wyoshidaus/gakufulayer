# GakufuLayer (楽譜レイヤー)

**GakufuLayer** is an early-stage public Python project intended for open-source licensing, focused on multilingual vocal and opera score PDF preparation. Its goal is to preserve musical notation while adding language-specific lyric translations, pronunciation (IPA), and other searchable annotation layers. Large scores are processed in manageable page blocks.

> **Status:** The initial prototype implements PDF page-block preprocessing and language-selection metadata. It **does not yet translate lyrics, produce IPA, or place annotations**. The existing Japanese-only VSOPER implementation has not yet been migrated or audited.

## Why multilingual?

Vocal scores are used across languages. Rather than assume Japanese is the only output, GakufuLayer treats the source lyric language and each requested target language as independent settings. A future translation stage can produce separate layers or output PDFs for each target language.

For example, one German source score may be prepared for both Japanese and English readers. A language setting is **metadata**, not evidence that translation is implemented or that a particular language has been quality-tested.

## Working features

- Split a score PDF into page-range blocks without rasterizing the music notation.
- Restrict preprocessing to selected 1-based pages (for example, pages 1–50).
- Create a JSON manifest linking blocks to source pages.
- Record a source language and multiple distinct target languages (common language-tag forms such as `de`, `ja`, `en`, `fr`, `zh-Hans`, and `pt-BR`).
- Run unit tests on synthetic PDF fixtures; no copyrighted score PDFs are bundled.

## Quick start

Requires Python 3.10 or newer.

```bash
python -m pip install -e '.[dev]'
gakufulayer preprocess path/to/score.pdf \
  --output-dir build/score --start-page 1 --end-page 50 --block-size 10 \
  --source-language de --target-language ja --target-language en
python -m pytest
```

Adjust `--end-page` if the source PDF contains fewer than 50 pages. Output includes `blocks/pages_0001-0010.pdf` and `manifest.json`. In the current version, the language flags only add a manifest entry such as:

```json
{"languages": {"source": "de", "targets": ["ja", "en"]}}
```

## Planned architecture

1. Extract lyric lines and associate them with score coordinates.
2. Import reviewed translations or connect replaceable translation providers, independently of the PDF engine.
3. Generate and review IPA for the **source language**; IPA is distinct from a translation.
4. Render independent annotation layers for target languages, respecting text direction, font coverage, line wrapping, and score geometry.
5. Validate text placement and assemble resumable page blocks into PDFs.

See [architecture](docs/architecture.md), [multilingual design](docs/multilingual.md), and [roadmap](docs/roadmap.md).

## Legal considerations

The project's code license does not grant rights to third-party score editions, lyric texts, or translations. Do not commit commercial scores, restricted editions, or unauthorized translations. Contributors should use synthetic PDFs or assets whose redistribution rights have been confirmed. Each user is responsible for checking rights to input and output materials in the relevant jurisdictions.

## Contributing and licensing

Read [CONTRIBUTING.md](CONTRIBUTING.md). The project currently has **no final OSS license**; Apache-2.0 is proposed but must be confirmed by the maintainer before it can be represented as an Apache-licensed project or submitted as a licensed OSS project.
