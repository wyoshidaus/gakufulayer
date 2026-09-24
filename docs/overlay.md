# Multilingual PDF text overlays

GakufuLayer can now add **reviewed, pre-positioned** translation text to a score PDF. This is an early rendering milestone, not automatic lyric detection or translation. The original page content is retained as PDF content: notation is **not rasterized**.

## Input

Create a UTF-8 JSON file with one source language and one or more placements:

~~~json
{
  "schema_version": "1.0",
  "source_language": "de",
  "placements": [
    {
      "source_ref": "seg-001",
      "page": 1,
      "language": "ja",
      "text": "こんばんは",
      "rect": [80, 445, 310, 475],
      "status": "reviewed",
      "reviewer": "example-reviewer",
      "font_size": 12
    },
    {
      "source_ref": "seg-001",
      "page": 1,
      "language": "en",
      "text": "Good evening",
      "rect": [80, 445, 310, 475],
      "status": "reviewed",
      "reviewer": "example-reviewer",
      "font_size": 12
    }
  ]
}
~~~

The example coordinates are for a **synthetic** demonstration document. They are not suitable for real scores without page-specific inspection. Rectangle coordinates are **PDF points** with a **top-left origin**; the four numbers mean [x0, y0, x1, y1]. Page numbers start at **1**. Reuse of the same rectangle between different languages is supported; overlapping rectangles **within** one language on the same page are currently rejected.

Only explicitly marked, reviewer-identified text may be rendered. Drafts must be reviewed first. The renderer cannot itself confirm translation accuracy or reviewer identity.

## Commands

~~~bash
python -m pip install -e '.[dev]'
gakufulayer render synthetic-score.pdf placements.json --output-dir build/out --combined
~~~

This writes one PDF per language and an optional combined PDF with PDF Optional Content Groups (OCGs):

- source filename + .ja.pdf
- source filename + .en.pdf
- source filename + .multilingual.pdf (when --combined is requested)

The combined PDF uses an OCG per language and configures the language groups as mutually exclusive viewer controls where supported. It defaults to displaying the first language listed in the JSON. **PDF viewers differ in OCG support**; use individual PDFs when a viewer does not expose layer controls.

## Fonts and RTL

Japanese and Chinese text use PyMuPDF's fallback Unicode rendering. For publication-grade typography and reproducible font coverage, pass licensed, locally available font paths. **Do not commit third-party font files.** For example:

~~~bash
gakufulayer render score.pdf placements.json \
  --output-dir build/out \
  --font ja=/absolute/path/to/JapaneseFont.otf \
  --font ar=/absolute/path/to/ArabicFont.ttf \
  --combined
~~~

Arabic, Hebrew and other detected right-to-left targets **require** an explicit .ttf or .otf font. The renderer uses HTML text shaping and validates extracted Unicode. Arabic with a suitable Noto font is included in the test suite. Other RTL scripts and font combinations need independent end-to-end validation.

## Validation

Before rendering, GakufuLayer rejects:
- unreviewed or empty translations;
- invalid / duplicate placements;
- rectangles outside the selected PDF page or overlapping rectangles for the same page and language;
- missing explicit fonts for RTL output.

It also checks text can fit above the configured minimum font size, verifies text extraction, and checks output page counts. Output PDFs are first staged in a temporary directory and published only after all complete successfully.

**Not yet implemented:** automatic detection of free spaces in a musical score, collision checking against music notation, automatic word-by-word lyric alignment, block-to-original-page remapping, and production-scale performance benchmarks. Visual inspection of annotated score pages is still necessary.

The Apache-2.0 license covers the project's own source code, not imported musical scores, copyrighted lyric texts, translations, or fonts.
