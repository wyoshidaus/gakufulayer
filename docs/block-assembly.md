# Score block assembly and page provenance

Split and rejoin arbitrary selected page ranges while preserving the original
PDF page objects. All page numbers in placement specs and manifests are **1-based**.

## Workflow

```bash
gakufulayer preprocess source.pdf --output-dir build/score \
  --start-page 1 --end-page 50 --block-size 10 \
  --source-language de --target-language ja --target-language en
gakufulayer assemble build/score/manifest.json build/score/selected.pdf \
  --source-pdf source.pdf --report build/score/page-map.json
gakufulayer remap-placements original-placements.json \
  build/score/page-map.json build/score/selected-placements.json
gakufulayer render build/score/selected.pdf \
  build/score/selected-placements.json \
  --output-dir build/score/rendered --combined
```

`assemble` sorts manifest blocks by original source page instead of trusting file
or JSON order. It rejects missing, duplicate, overlapping and out-of-range blocks.
When an original source PDF is supplied, it compares each selected page's
MediaBox/CropBox/rotation and extracted text against that source PDF.
An unverified page with only image content cannot be proven identical by text
checks; notation and image-content QC still requires targeted visual inspection.

The assembly report's `page_mapping` contains records such as
`{"source_page": 50, "output_page": 50, "block_page": 10, ...}`.
For a source selection beginning at page 12, original page 12 becomes output
page 1. Remapping writes a *new* placement JSON and records the original
`source_page` alongside the rewritten output-relative `page`. It rejects
out-of-range placements and refuses to remap a JSON that is already remapped.

The renderer continues to use **output-relative** `page` positions. The
metadata field `source_page` is for review and provenance, not automatic
coordinate correction. Original lyric coordinates must be verified against the
selected blocks if they had non-default page boxes or rotations.

## Limitations

- No OCR and no per-page image hash (optimized for long opera scores).
- Extractable text checks can detect swapped text-based pages but cannot fully
  authenticate an image-only page.
- If blocks have been edited rather than simply split, verify bounding boxes
  and visual layout on affected pages.
- Source PDFs and translation content are not committed to the public project.
