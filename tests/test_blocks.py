"""Tests for source-page provenance; only synthetic score PDFs are used."""

import json
from pathlib import Path

import fitz
import pytest

from gakufulayer.blocks import assemble_blocks, remap_placements
from gakufulayer.overlay import render_layers
from gakufulayer.preprocess import split_pdf


def make_source(path: Path, pages: int = 6) -> None:
    with fitz.open() as doc:
        for i in range(1, pages + 1):
            page = doc.new_page(width=500, height=300)
            page.insert_text((25, 30), f"ORIGINAL PAGE {i}")
            page.draw_line((25, 180), (475, 180), width=1)
        doc.save(path)


def write_placements(path: Path, page: int) -> None:
    data = {
        "schema_version": "1.0",
        "source_language": "de",
        "placements": [
            {
                "source_ref": "seg-en", "page": page, "language": "en",
                "text": "A longer English translation for this musical phrase",
                "rect": [25, 60, 470, 130], "status": "reviewed",
                "reviewer": "synthetic-reviewer",
            },
            {
                "source_ref": "seg-ja", "page": page, "language": "ja",
                "text": "こんばんは", "rect": [25, 60, 250, 110],
                "status": "reviewed", "reviewer": "synthetic-reviewer",
            },
        ],
    }
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


def test_reassemble_subset_and_render_remapped_multilingual_layers(tmp_path):
    source = tmp_path / "original.pdf"
    make_source(source)
    manifest = split_pdf(source, tmp_path / "prep", start_page=2, end_page=5, block_size=2)
    # Manifest order must not dictate the output order.
    manifest["blocks"].reverse()
    manifest_path = tmp_path / "prep" / "manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    assembled = tmp_path / "assembled.pdf"
    report = assemble_blocks(manifest_path, assembled, source_pdf=source)
    assert [(r["source_page"], r["output_page"]) for r in report["page_mapping"]] == [
        (2, 1), (3, 2), (4, 3), (5, 4)
    ]
    assert report["text_checked_pages"] == 4
    with fitz.open(assembled) as doc:
        assert doc.page_count == 4
        assert [f"ORIGINAL PAGE {i + 2}" in doc[i].get_text() for i in range(4)] == [True] * 4
        assert all(len(doc[i].get_drawings()) == 1 for i in range(4))

    placements = tmp_path / "original_placements.json"
    write_placements(placements, page=5)
    report_file = tmp_path / "report.json"
    report_file.write_text(json.dumps(report), encoding="utf-8")
    mapped_file = tmp_path / "mapped.json"
    remapped = remap_placements(placements, report_file, mapped_file)
    assert remapped["mapped_source_pages"] == [5]
    mapped = json.loads(mapped_file.read_text(encoding="utf-8"))
    assert {(item["source_page"], item["page"]) for item in mapped["placements"]} == {(5, 4)}
    result = render_layers(assembled, mapped_file, tmp_path / "rendered", combined=True)
    with fitz.open(result["outputs"]["en"]) as doc:
        assert "A longer English translation" not in doc[2].get_text()
        assert "A longer English translation" in doc[3].get_text()
        assert "ORIGINAL PAGE 5" in doc[3].get_text()
    with fitz.open(result["outputs"]["ja"]) as doc:
        assert "こんばんは" in doc[3].get_text()
    with fitz.open(result["outputs"]["combined"]) as doc:
        assert len(doc.get_ocgs()) == 2


@pytest.mark.parametrize("kind", ["missing", "overlap", "wrong_count", "swapped"])
def test_reassembly_fails_closed_on_corrupt_blocks(tmp_path, kind):
    source = tmp_path / "original.pdf"
    make_source(source)
    manifest = split_pdf(source, tmp_path / "prep", start_page=2, end_page=5, block_size=2)
    if kind == "missing":
        (tmp_path / "prep" / manifest["blocks"][1]["file"]).unlink()
    elif kind == "overlap":
        manifest["blocks"][1]["start_page"] = 3
    elif kind == "wrong_count":
        manifest["blocks"][0]["page_count"] = 3
    elif kind == "swapped":
        left, right = manifest["blocks"]
        left["file"], right["file"] = right["file"], left["file"]
    manifest_file = tmp_path / "prep" / "manifest.json"
    manifest_file.write_text(json.dumps(manifest), encoding="utf-8")
    assembled = tmp_path / "assembled.pdf"
    with pytest.raises((ValueError, FileNotFoundError)):
        assemble_blocks(manifest_file, assembled, source_pdf=source)
    assert not assembled.exists()


def test_remap_rejects_page_outside_selected_range_and_double_remap(tmp_path):
    source = tmp_path / "original.pdf"
    make_source(source)
    split_pdf(source, tmp_path / "prep", start_page=2, end_page=5, block_size=2)
    report = assemble_blocks(tmp_path / "prep" / "manifest.json", tmp_path / "joined.pdf")
    report_file = tmp_path / "mapping.json"
    report_file.write_text(json.dumps(report), encoding="utf-8")
    spec = tmp_path / "original.json"
    write_placements(spec, page=6)
    with pytest.raises(ValueError, match="unselected"):
        remap_placements(spec, report_file, tmp_path / "mapped.json")
    assert not (tmp_path / "mapped.json").exists()

    write_placements(spec, page=5)
    mapped = tmp_path / "mapped.json"
    remap_placements(spec, report_file, mapped)
    with pytest.raises(ValueError, match="twice"):
        remap_placements(mapped, report_file, tmp_path / "mapped-twice.json")
