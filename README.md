# GakufuLayer (楽譜レイヤー)

**GakufuLayer** is an early-stage open-source Python project focused on multilingual vocal and opera score PDF preparation. Its goal is to preserve musical notation while adding language-specific lyric translations, pronunciation (IPA), and other searchable annotation layers. Large scores are processed in manageable page blocks.

> **Status:** Working prototypes include PDF page-block preprocessing, language selection, VSOPER-derived translation-result validation/atomic commits, a provider-neutral interface with a reviewed-text adapter, and selectable PDF text overlays from **reviewed, manually positioned** translations. **Automatic lyric extraction, machine translation, IPA generation, and automatic score-aware placement are not implemented.**

## Why multilingual?

Vocal scores are used across languages. Rather than assume Japanese is the only output, GakufuLayer treats the source lyric language and each requested target language as independent settings. A future translation stage can produce separate layers or output PDFs for each target language.

For example, one German source score may be prepared for both Japanese and English readers. A language setting is **metadata**, not evidence that translation is implemented or that a particular language has been quality-tested.

## Working features

- Split a score PDF into page-range blocks without rasterizing the music notation.
- Restrict preprocessing to selected 1-based pages (for example, pages 1–50).
- Create a JSON manifest linking blocks to source pages.
- Record a source language and multiple distinct target languages (common language-tag forms such as `de`, `ja`, `en`, `fr`, `zh-Hans`, and `pt-BR`).
- Validate and atomically commit ChatGPT- or human-produced translation-unit text for any declared target language.
- Render **reviewed** translations with supplied coordinates into one PDF per language, and optionally an OCG-toggleable combined multilingual PDF.
- Render tested Japanese and Latin examples with Unicode text extraction; Arabic requires an explicit, tested font.
- Run unit tests on synthetic PDF fixtures; no copyrighted score PDFs or font files are bundled.

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

## Reassemble page blocks and preserve page references

For a selected range of a long score, join the generated blocks and produce an explicit
source-page → output-page map before applying reviewed placements:

```bash
gakufulayer assemble build/score/manifest.json build/score/selected.pdf \
  --source-pdf path/to/score.pdf --report build/score/page-map.json
gakufulayer remap-placements original-placements.json \
  build/score/page-map.json build/score/selected-placements.json
gakufulayer render build/score/selected.pdf \
  build/score/selected-placements.json --output-dir build/score/rendered --combined
```

The assembly step orders blocks by their original page numbers, rejects missing or
overlapping ranges, and checks source-page dimensions and extractable text when
`--source-pdf` is given. The remapping step converts original page references, for
example source page 5 → assembled page 4. It refuses placements outside the selected
range or placements already remapped. This does not replace visual checks for
image-only score pages.

## Translation and PDF rendering

The rendering step requires a **reviewed, pre-positioned** JSON placement document. It does not discover empty spaces on the score automatically. The sample in [examples/placements.synthetic.json](examples/placements.synthetic.json) is for a synthetic PDF only.

```bash
python examples/create_synthetic_score.py synthetic-score.pdf
gakufulayer render synthetic-score.pdf examples/placements.synthetic.json \
  --output-dir build/translated --combined
```

The combined PDF contains one optional content group per target language, enabling layer switching in compatible viewers. See [PDF overlay usage and limitations](docs/overlay.md) and [VSOPER migration audit](docs/vsoper-migration.md).

## Planned architecture

1. Extract and align lyric lines and source coordinates automatically.
2. Connect real translation providers as replaceable adapters; keep human review mandatory for publication output.
3. Generate and review IPA for the **source language**; IPA is distinct from translation.
4. Plan score-aware placement without collisions, support more tested scripts and verify large-score page-block reassembly.
5. Benchmark resumable workflows on legally usable large scores.

See [architecture](docs/architecture.md), [multilingual design](docs/multilingual.md), and [roadmap](docs/roadmap.md).

## Legal considerations

The project's code license does not grant rights to third-party score editions, lyric texts, or translations. Do not commit commercial scores, restricted editions, or unauthorized translations. Contributors should use synthetic PDFs or assets whose redistribution rights have been confirmed. Each user is responsible for checking rights to input and output materials in the relevant jurisdictions.

## Contributing and licensing

Read [CONTRIBUTING.md](CONTRIBUTING.md). GakufuLayer is licensed under the Apache License 2.0. Third-party scores, lyric texts, translations, fonts and other assets remain subject to their own rights. **Important dependency:** the current PDF renderer uses PyMuPDF, offered under AGPLv3 or commercial terms. Deployment and distribution obligations are under review in [issue #5](https://github.com/wyoshidaus/gakufulayer/issues/5); the Apache-2.0 declaration applies to this project's own source, not the entire runtime stack.


## Multilingual PDF layers

GakufuLayer can now render prepared translation text into independent PDF Optional Content Groups (OCGs), one layer per target language. Supporting PDF viewers can show or hide these layers without changing the original score content.

The renderer uses PyMuPDF's shaped HTML text path so CJK and right-to-left scripts can be handled by the same pipeline. The input is a JSON layer plan with page rectangles and explicit language tags. This stage **does not translate text or discover score coordinates**; it renders already prepared text.

Example:

~~~bash
gakufulayer render-layers score.pdf layers.json layered-score.pdf
~~~

See [multilingual PDF layers](docs/pdf-layers.md).
