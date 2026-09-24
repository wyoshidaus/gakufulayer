"""CLI smoke test for the multilingual PDF renderer."""

import json

import fitz

from gakufulayer.cli import main


def test_render_command_creates_independent_and_combined_pdfs(tmp_path, capsys):
    source = tmp_path / "synthetic.pdf"
    with fitz.open() as doc:
        doc.new_page(width=595, height=842)
        doc.save(source)

    spec = tmp_path / "placements.json"
    spec.write_text(
        json.dumps(
            {
                "schema_version": "1.0",
                "source_language": "de",
                "placements": [
                    {
                        "source_ref": "unit-1",
                        "page": 1,
                        "language": "ja",
                        "text": "こんばんは",
                        "rect": [50, 100, 350, 145],
                        "status": "reviewed",
                        "reviewer": "synthetic-test",
                    },
                    {
                        "source_ref": "unit-1",
                        "page": 1,
                        "language": "en",
                        "text": "Good evening",
                        "rect": [50, 100, 350, 145],
                        "status": "reviewed",
                        "reviewer": "synthetic-test",
                    },
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    output = tmp_path / "out"
    result = main(
        [
            "render", str(source), str(spec), "--output-dir", str(output),
            "--combined", "--report", str(tmp_path / "report.json"),
        ]
    )
    assert result == 0
    assert json.loads(capsys.readouterr().out)["languages"] == ["ja", "en"]
    assert (output / "synthetic.ja.pdf").is_file()
    assert (output / "synthetic.en.pdf").is_file()
    assert (output / "synthetic.multilingual.pdf").is_file()
    assert json.loads((tmp_path / "report.json").read_text())["annotation_count"] == 2
