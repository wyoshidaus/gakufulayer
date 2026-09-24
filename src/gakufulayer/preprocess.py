"""Split a score PDF into bounded page blocks and a reproducible manifest."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

from gakufulayer.languages import configure_languages
from pypdf import PdfReader, PdfWriter


def split_pdf(
    input_pdf: str | Path,
    output_dir: str | Path,
    *,
    start_page: int = 1,
    end_page: int | None = None,
    block_size: int = 10,
    source_language: str | None = None,
    target_languages: Iterable[str] | None = None,
) -> dict:
    """Split a PDF into page blocks, using 1-based inclusive page ranges.

    Returns the manifest and writes it to output_dir/manifest.json.
    No source-page image hashes or OCR are performed.
    """
    languages = configure_languages(source_language, target_languages)
    source = Path(input_pdf)
    destination = Path(output_dir)
    if block_size < 1:
        raise ValueError("block_size must be at least 1")
    if start_page < 1:
        raise ValueError("start_page must be at least 1")
    if not source.is_file():
        raise FileNotFoundError(f"Input PDF not found: {source}")

    reader = PdfReader(str(source))
    total_pages = len(reader.pages)
    last_page = total_pages if end_page is None else end_page
    if last_page < start_page or last_page > total_pages:
        raise ValueError(
            f"Invalid page range {start_page}–{last_page}; "
            f"the PDF contains {total_pages} pages"
        )

    block_dir = destination / "blocks"
    block_dir.mkdir(parents=True, exist_ok=True)
    blocks = []
    for first in range(start_page, last_page + 1, block_size):
        last = min(first + block_size - 1, last_page)
        filename = f"pages_{first:04d}-{last:04d}.pdf"
        relative_path = Path("blocks") / filename
        writer = PdfWriter()
        for page_number in range(first, last + 1):
            writer.add_page(reader.pages[page_number - 1])
        with (destination / relative_path).open("wb") as stream:
            writer.write(stream)
        blocks.append(
            {
                "start_page": first,
                "end_page": last,
                "page_count": last - first + 1,
                "file": relative_path.as_posix(),
            }
        )

    manifest = {
        "schema_version": "1.1",
        "source_filename": source.name,
        "source_page_count": total_pages,
        "start_page": start_page,
        "end_page": last_page,
        "block_size": block_size,
        "languages": languages.to_manifest(),
        "blocks": blocks,
    }
    (destination / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return manifest
