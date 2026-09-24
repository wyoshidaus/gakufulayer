"""Synthetic metadata audit tests: protect both /Info and XMP independently."""

from __future__ import annotations

import json
from pathlib import Path

import fitz
import pytest

from gakufulayer.overlay import render_layers
from gakufulayer.pdf_metadata import audit_pdf_metadata


XMP = (
    '<?xpacket begin="\ufeff" id="W5M0MpCehiHzreSzNTczkc9d"?>'
    '<x:xmpmeta xmlns:x="adobe:ns:meta/">'
    '<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">'
    '<rdf:Description rdf:about="" xmlns:dc="http://purl.org/dc/elements/1.1/">'
    '<dc:rights><rdf:Alt><rdf:li xml:lang="x-default">'
    'Synthetic rights notice: keep this XMP.'
    '</rdf:li></rdf:Alt></dc:rights>'
    '</rdf:Description></rdf:RDF></x:xmpmeta><?xpacket end="w"?>'
)


def make_source(path: Path) -> None:
    with fitz.open() as doc:
        page = doc.new_page(width=480, height=250)
        page.insert_text((20, 25), "SOURCE MUSIC")
        doc.set_metadata({
            "title": "Synthetic score title",
            "author": "Synthetic author",
            "subject": "Synthetic licensing notice",
            "creator": "Synthetic creator",
            "producer": "Synthetic PDF producer",
        })
        doc.set_xml_metadata(XMP)
        doc.save(path)


def make_spec(path: Path) -> None:
    path.write_text(
        json.dumps({
            "schema_version": "1.0",
            "source_language": "de",
            "placements": [
                {
                    "source_ref": "seg-ja", "page": 1, "language": "ja",
                    "text": "こんばんは", "rect": [30, 55, 320, 115],
                    "status": "reviewed", "reviewer": "synthetic",
                },
                {
                    "source_ref": "seg-en", "page": 1, "language": "en",
                    "text": "Good evening", "rect": [30, 55, 320, 115],
                    "status": "reviewed", "reviewer": "synthetic",
                },
            ],
        }, ensure_ascii=False),
        encoding="utf-8",
    )


def test_metadata_retained_in_language_pdfs_and_ocg_output(tmp_path):
    source = tmp_path / "score.pdf"
    make_source(source)
    spec = tmp_path / "placements.json"
    make_spec(spec)
    result = render_layers(source, spec, tmp_path / "out", combined=True)
    assert set(result["metadata_audit"]) == {"ja", "en", "combined"}
    for tag, output in result["outputs"].items():
        report = audit_pdf_metadata(source, output)
        assert report["status"] == "pass", (tag, report)
        assert report["source_has_xmp"] and report["output_has_xmp"]
        assert any(c["field"] == "/Producer" and c["status"] == "pass"
                   for c in report["checks"])
        assert result["metadata_audit"][tag]["status"] == "pass"
        assert not any("Synthetic rights notice:" in str(v)
                       for v in result["metadata_audit"][tag].values())


def test_metadata_audit_fails_if_info_or_xmp_not_preserved(tmp_path):
    original = tmp_path / "original.pdf"
    make_source(original)
    missing_producer = tmp_path / "changed.pdf"
    with fitz.open(original) as doc:
        metadata = dict(doc.metadata)
        metadata["producer"] = "Changed producer"
        doc.set_metadata(metadata)
        doc.save(missing_producer)
    report = audit_pdf_metadata(original, missing_producer)
    assert report["status"] == "fail"
    assert any(c["field"] == "/Producer" and c["status"] == "fail"
               for c in report["checks"])

    missing_xmp = tmp_path / "missing-xmp.pdf"
    with fitz.open(original) as doc:
        doc.del_xml_metadata()
        doc.save(missing_xmp)
    report = audit_pdf_metadata(original, missing_xmp)
    assert report["status"] == "fail"
    assert any(c["field"] == "XMP" and c["status"] == "fail"
               for c in report["checks"])


def test_missing_producer_returns_review_required_not_legal_clearance(tmp_path):
    source = tmp_path / "without-producer.pdf"
    with fitz.open() as doc:
        doc.new_page()
        doc.save(source)
    output = tmp_path / "copy.pdf"
    with fitz.open(source) as doc:
        doc[0].insert_text((20, 40), "hello")
        doc.save(output)
    report = audit_pdf_metadata(source, output)
    assert report["status"] == "review_required"
    assert any(c["reason"] == "output_has_no_producer_notice_manual_review_required"
               for c in report["checks"])


def test_renderer_stages_outputs_until_metadata_audit_passes(tmp_path, monkeypatch):
    source = tmp_path / "source.pdf"
    make_source(source)
    spec = tmp_path / "placements.json"
    make_spec(spec)
    import gakufulayer.overlay as overlay

    def reject_all(*_args, **_kwargs):
        return {"status": "fail", "checks": [{"field": "/Producer", "status": "fail"}]}

    monkeypatch.setattr(overlay, "audit_pdf_metadata", reject_all)
    with pytest.raises(ValueError, match="Metadata provenance audit failed"):
        overlay.render_layers(source, spec, tmp_path / "out", combined=True)
    assert not list((tmp_path / "out").glob("*.pdf"))


def test_source_notice_survives_preprocess_and_assembly(tmp_path):
    from gakufulayer.blocks import assemble_blocks
    from gakufulayer.preprocess import split_pdf

    source = tmp_path / "source-with-rights.pdf"
    make_source(source)
    manifest = split_pdf(source, tmp_path / "blocks", block_size=1)
    block = tmp_path / "blocks" / manifest["blocks"][0]["file"]
    assert audit_pdf_metadata(source, block)["status"] == "pass"

    assembled = tmp_path / "assembled.pdf"
    report = assemble_blocks(tmp_path / "blocks" / "manifest.json", assembled, source_pdf=source)
    assert report["metadata_from"] == "original_source_pdf"
    assert audit_pdf_metadata(source, assembled)["status"] == "pass"

    no_original = tmp_path / "assembled-from-block.pdf"
    fallback = assemble_blocks(tmp_path / "blocks" / "manifest.json", no_original)
    assert fallback["metadata_from"] == "first_block_unverified"
    assert audit_pdf_metadata(source, no_original)["status"] == "pass"
