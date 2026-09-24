"""Reassemble preprocessed PDF blocks with explicit source-page provenance.

All page numbers in manifests and placement specs are one-based. Reassembly
does not rasterize pages or calculate source-page image hashes.
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any

from pypdf import PdfReader, PdfWriter


def _positive_int(value: Any, name: str) -> int:
    if type(value) is not int or value < 1:
        raise ValueError(f"{name} must be a positive integer")
    return value


def _page_geometry(page: Any) -> tuple:
    def box_coordinates(box: Any) -> tuple[float, ...]:
        return tuple(round(float(n), 3) for n in box)
    return (
        box_coordinates(page.mediabox),
        box_coordinates(page.cropbox),
        int(page.get("/Rotate", 0) or 0) % 360,
    )


def _normalized_text(page: Any) -> str:
    return " ".join((page.extract_text() or "").split())


def _write_json_atomic(output: Path, payload: dict[str, Any]) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{output.name}.", suffix=".tmp", dir=output.parent)
    tmp = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, output)
    finally:
        tmp.unlink(missing_ok=True)


def assemble_blocks(
    manifest_path: str | Path,
    output_pdf: str | Path,
    *,
    source_pdf: str | Path | None = None,
) -> dict[str, Any]:
    """Join selected blocks in source order and report original-to-output mapping.

    Optional source_pdf enables page-geometry and extractable-text comparison
    against original pages. Image-only content cannot be proven identical by
    these structural checks; visual/source-specific QC remains necessary.
    """
    manifest_file = Path(manifest_path).resolve()
    root = manifest_file.parent
    manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
    if manifest.get("schema_version") != "1.1":
        raise ValueError("Expected preprocessing manifest schema_version 1.1")
    start = _positive_int(manifest.get("start_page"), "start_page")
    end = _positive_int(manifest.get("end_page"), "end_page")
    total = _positive_int(manifest.get("source_page_count"), "source_page_count")
    if not start <= end <= total:
        raise ValueError("Manifest page range exceeds source_page_count")
    records = manifest.get("blocks")
    if not isinstance(records, list) or not records:
        raise ValueError("Manifest has no page blocks")

    dest = Path(output_pdf).resolve()
    original = Path(source_pdf).resolve() if source_pdf is not None else None
    if original is not None and dest == original:
        raise ValueError("Output PDF must differ from source PDF")
    original_reader = PdfReader(str(original)) if original is not None else None
    if original_reader is not None and len(original_reader.pages) != total:
        raise ValueError("Source PDF page count does not match manifest")

    ordered = sorted(records, key=lambda record: _positive_int(record.get("start_page"), "block start_page"))
    writer = PdfWriter()
    mapping: list[dict[str, Any]] = []
    next_source = start
    verified_text_pages = 0
    paths: set[Path] = set()

    for record in ordered:
        first = _positive_int(record.get("start_page"), "block start_page")
        last = _positive_int(record.get("end_page"), "block end_page")
        declared_count = _positive_int(record.get("page_count"), "block page_count")
        if first != next_source or last < first or last > end:
            raise ValueError(f"Gap, overlap, or out-of-range block at source page {first}")
        if declared_count != last - first + 1:
            raise ValueError(f"Block {first}-{last} declares incorrect page_count")

        filename = record.get("file")
        if not isinstance(filename, str) or not filename.strip():
            raise ValueError("Block file path is missing")
        relative = Path(filename)
        if relative.is_absolute() or not (root / relative).resolve().is_relative_to(root):
            raise ValueError(f"Block path escapes manifest directory: {filename}")
        block = (root / relative).resolve()
        if block in paths:
            raise ValueError(f"Duplicate block file: {filename}")
        paths.add(block)
        if block == dest:
            raise ValueError("Output PDF must not overwrite a block")
        if not block.is_file():
            raise FileNotFoundError(f"Block not found: {block}")

        reader = PdfReader(str(block))
        if len(reader.pages) != declared_count:
            raise ValueError(f"Block {filename} has unexpected PDF page count")

        for index, page in enumerate(reader.pages):
            source_page = first + index
            if original_reader is not None:
                expected = original_reader.pages[source_page - 1]
                if _page_geometry(page) != _page_geometry(expected):
                    raise ValueError(f"Geometry mismatch at source page {source_page}")
                actual_text = _normalized_text(page)
                expected_text = _normalized_text(expected)
                if actual_text != expected_text:
                    raise ValueError(f"Text mismatch at source page {source_page}; block order may be wrong")
                if expected_text:
                    verified_text_pages += 1
            writer.add_page(page)
            mapping.append({
                "source_page": source_page,
                "output_page": len(mapping) + 1,
                "block_file": filename,
                "block_page": index + 1,
            })
        next_source = last + 1

    if next_source != end + 1 or len(mapping) != end - start + 1:
        raise ValueError("Selected manifest range is not fully covered")

    dest.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{dest.stem}.", suffix=".pdf", dir=dest.parent)
    tmp = Path(tmp_name)
    try:
        with os.fdopen(fd, "wb") as handle:
            writer.write(handle)
            handle.flush()
            os.fsync(handle.fileno())
        if len(PdfReader(str(tmp)).pages) != len(mapping):
            raise ValueError("Assembled PDF failed final page-count verification")
        os.replace(tmp, dest)
    finally:
        tmp.unlink(missing_ok=True)

    return {
        "schema_version": "1.0",
        "source_manifest": str(manifest_file),
        "output_pdf": str(dest),
        "source_page_count": total,
        "start_page": start,
        "end_page": end,
        "output_page_count": len(mapping),
        "source_pdf_compared": original is not None,
        "text_checked_pages": verified_text_pages,
        "page_mapping": mapping,
    }


def remap_placements(
    original_placements: str | Path,
    assembly_report: str | Path,
    output_placements: str | Path,
) -> dict[str, Any]:
    """Convert original-source page numbers to assembled PDF page numbers."""
    raw = json.loads(Path(original_placements).read_text(encoding="utf-8"))
    report = json.loads(Path(assembly_report).read_text(encoding="utf-8"))
    if raw.get("schema_version") != "1.0":
        raise ValueError("Expected placement schema_version 1.0")
    records = report.get("page_mapping")
    if not isinstance(records, list) or not records:
        raise ValueError("Assembly report contains no page mapping")
    mapping: dict[int, int] = {}
    outputs: set[int] = set()
    for record in records:
        source = _positive_int(record.get("source_page"), "source_page")
        output = _positive_int(record.get("output_page"), "output_page")
        if source in mapping or output in outputs:
            raise ValueError("Assembly report contains duplicate source or output page")
        mapping[source] = output
        outputs.add(output)
    if outputs != set(range(1, len(records) + 1)):
        raise ValueError("Assembly report output pages are not contiguous")

    original_items = raw.get("placements")
    if not isinstance(original_items, list) or not original_items:
        raise ValueError("Placement specification has no placements")
    rewritten = []
    for record in original_items:
        if "source_page" in record:
            raise ValueError("Placement already has source_page; refusing to remap twice")
        original_page = _positive_int(record.get("page"), "placement page")
        if original_page not in mapping:
            raise ValueError(f"Placement references unselected source page {original_page}")
        rewritten.append({**record, "source_page": original_page, "page": mapping[original_page]})

    output = Path(output_placements).resolve()
    if output == Path(original_placements).resolve():
        raise ValueError("Remapped placements must use a new output file")
    _write_json_atomic(output, {**raw, "placements": rewritten})
    return {
        "output_placements": str(output),
        "placement_count": len(rewritten),
        "mapped_source_pages": sorted({r["source_page"] for r in rewritten}),
    }
