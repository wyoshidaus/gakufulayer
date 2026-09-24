"""Tests use synthetic PDFs, not published scores."""

import json

import pytest
from pypdf import PdfReader, PdfWriter

from gakufulayer.cli import main
from gakufulayer.preprocess import split_pdf


def make_pdf(path, pages=5):
    writer = PdfWriter()
    for _ in range(pages):
        writer.add_blank_page(width=300, height=400)
    with path.open("wb") as stream:
        writer.write(stream)


def test_selected_range_and_manifest(tmp_path):
    source = tmp_path / "synthetic.pdf"
    make_pdf(source)
    output = tmp_path / "output"
    manifest = split_pdf(source, output, start_page=2, end_page=5, block_size=2)
    assert [(b["start_page"], b["end_page"]) for b in manifest["blocks"]] == [
        (2, 3), (4, 5)
    ]
    assert [len(PdfReader(str(output / b["file"])).pages) for b in manifest["blocks"]] == [2, 2]
    assert json.loads((output / "manifest.json").read_text(encoding="utf-8")) == manifest


@pytest.mark.parametrize("start,end,size", [(0, 3, 2), (3, 2, 2), (1, 6, 2), (1, 2, 0)])
def test_invalid_ranges(tmp_path, start, end, size):
    source = tmp_path / "synthetic.pdf"
    make_pdf(source)
    with pytest.raises(ValueError):
        split_pdf(source, tmp_path / "output", start_page=start, end_page=end, block_size=size)


def test_cli(tmp_path, capsys):
    source = tmp_path / "synthetic.pdf"
    make_pdf(source, pages=3)
    result = main(["preprocess", str(source), "--output-dir", str(tmp_path / "out"), "--block-size", "2"])
    assert result == 0
    assert "Created 2 block(s)" in capsys.readouterr().out


def test_manifest_retains_multiple_target_languages(tmp_path):
    source = tmp_path / "synthetic.pdf"
    make_pdf(source, pages=2)
    manifest = split_pdf(
        source,
        tmp_path / "out",
        source_language="DE",
        target_languages=["ja", "en", "JA"],
    )
    assert manifest["schema_version"] == "1.1"
    assert manifest["languages"] == {"source": "de", "targets": ["ja", "en"]}


def test_cli_multilingual_metadata(tmp_path):
    source = tmp_path / "synthetic.pdf"
    make_pdf(source, pages=2)
    output = tmp_path / "output"
    result = main(
        [
            "preprocess", str(source), "--output-dir", str(output),
            "--source-language", "fr", "--target-language", "ja",
            "--target-language", "en",
        ]
    )
    assert result == 0
    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["languages"] == {"source": "fr", "targets": ["ja", "en"]}
