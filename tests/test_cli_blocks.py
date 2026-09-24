"""End-to-end CLI for block assembly and original-page placement remapping."""
import json

import fitz

from gakufulayer.cli import main


def test_cli_assemble_and_remap(tmp_path, capsys):
    source = tmp_path / "source.pdf"
    with fitz.open() as doc:
        for n in range(3):
            page = doc.new_page(width=400, height=300)
            page.insert_text((20, 20), f"SOURCE-{n + 1}")
        doc.save(source)

    out = tmp_path / "prep"
    assert main(["preprocess", str(source), "--output-dir", str(out),
                 "--start-page", "2", "--end-page", "3", "--block-size", "1"]) == 0
    joined = tmp_path / "joined.pdf"
    report_file = tmp_path / "mapping.json"
    assert main(["assemble", str(out / "manifest.json"), str(joined),
                 "--source-pdf", str(source), "--report", str(report_file)]) == 0
    report = json.loads(report_file.read_text(encoding="utf-8"))
    assert report["page_mapping"][0]["source_page"] == 2
    placements = tmp_path / "original_placements.json"
    placements.write_text(json.dumps({
        "schema_version": "1.0", "source_language": "de",
        "placements": [{
            "source_ref": "seg-1", "page": 3, "language": "en",
            "text": "Good evening", "rect": [30, 60, 320, 110],
            "status": "reviewed", "reviewer": "synthetic",
        }],
    }), encoding="utf-8")
    mapped = tmp_path / "mapped.json"
    assert main(["remap-placements", str(placements), str(report_file),
                 str(mapped)]) == 0
    assert json.loads(mapped.read_text())["placements"][0]["page"] == 2
    rendered_dir = tmp_path / "rendered"
    assert main(["render", str(joined), str(mapped),
                 "--output-dir", str(rendered_dir)]) == 0
    with fitz.open(rendered_dir / "joined.en.pdf") as doc:
        assert "Good evening" in doc[1].get_text()
        assert "Good evening" not in doc[0].get_text()
