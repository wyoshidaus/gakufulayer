"""CLI exit code smoke test for core-only PDF metadata provenance audits."""

from __future__ import annotations

import json

import fitz

from gakufulayer.cli import main


def test_core_metadata_audit_cli_reports_preserved_info(tmp_path, capsys):
    source = tmp_path / "source.pdf"
    output = tmp_path / "output.pdf"
    with fitz.open() as doc:
        doc.new_page()
        doc.set_metadata({"title": "Synthetic source", "producer": "Synthetic producer"})
        doc.save(source)
    with fitz.open(source) as doc:
        doc[0].insert_text((30, 50), "Hello")
        doc.save(output)
    report_path = tmp_path / "metadata.json"
    result = main(["audit-metadata", str(source), str(output), "--report", str(report_path)])
    assert result == 0
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["status"] == "pass"
    assert "Synthetic producer" not in capsys.readouterr().out


def test_core_metadata_audit_cli_returns_nonzero_when_changed(tmp_path):
    source = tmp_path / "source.pdf"
    output = tmp_path / "output.pdf"
    with fitz.open() as doc:
        doc.new_page()
        doc.set_metadata({"producer": "Original synthetic producer"})
        doc.save(source)
    with fitz.open(source) as doc:
        doc.set_metadata({"producer": "Changed synthetic producer"})
        doc.save(output)
    assert main(["audit-metadata", str(source), str(output)]) == 2
