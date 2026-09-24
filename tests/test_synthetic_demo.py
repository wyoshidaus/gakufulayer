"""End-to-end synthetic demo uses only test-created PDFs and existing text fixtures."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

import pymupdf as fitz


REPO = Path(__file__).resolve().parents[1]


def test_rights_safe_demo_runs_full_pipeline(tmp_path):
    destination = tmp_path / "output"
    result = subprocess.run(
        [
            sys.executable, str(REPO / "examples" / "run_synthetic_demo.py"),
            "--output-dir", str(destination),
        ],
        check=True, capture_output=True, text=True, cwd=REPO,
    )
    printed = json.loads(result.stdout.strip().splitlines()[-1])
    assert printed["status"] == "pass"
    assert printed["languages"] == ["en", "ja"]
    report = json.loads((destination / "demo-report.json").read_text(encoding="utf-8"))
    assert report["real_score_tested"] is False
    assert report["automatic_translation"] is False
    assert report["automatic_placement"] is False
    assert report["page_mapping_verified"] is True
    assert set(report["output_files"]) == {"ja", "en", "combined"}
    for language, verification in report["languages"].items():
        assert verification["extracted_text_matches"]
        assert verification["source_text_preserved"]
        assert verification["notation_line_drawings_preserved"]
        output = destination / report["output_files"][language]
        with fitz.open(output) as doc:
            assert doc.page_count == 1
            assert "Guten Abend" in doc[0].get_text()
    assert report["combined"]["layers"] == ["GakufuLayer: en", "GakufuLayer: ja"]
    assert report["combined"]["notation_line_drawings_preserved"] is True
    assert report["combined"]["metadata_provenance"] in {"pass", "review_required"}
    assert "separate review" in report["license_clearance"]
