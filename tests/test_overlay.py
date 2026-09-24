"""Synthetic PDF tests: no copyrighted score or font assets are bundled."""

import json
import shutil
import subprocess
import unicodedata
from pathlib import Path

import fitz
import pytest

from gakufulayer.overlay import render_layers


def fixture_pdf(path: Path) -> None:
    with fitz.open() as doc:
        page = doc.new_page(width=500, height=300)
        page.draw_line((20, 100), (480, 100), width=1)
        page.insert_text((30, 35), "SOURCE-MARKER")
        doc.new_page(width=500, height=300)
        doc.save(path)


def layer_spec(path: Path, languages=("ja", "en")) -> None:
    text = {"ja": "こんばんは", "en": "Good evening", "fr": "Bonsoir"}
    data = {
        "schema_version": "1.0",
        "source_language": "de",
        "placements": [
            {
                "source_ref": "seg1",
                "page": 1,
                "language": language,
                "text": text[language],
                "status": "reviewed",
                "reviewer": "example-reviewer",
                "rect": [30, 45, 320, 83],
            }
            for language in languages
        ],
    }
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


def test_independent_language_outputs_preserve_source(tmp_path):
    source = tmp_path / "synthetic.pdf"
    spec = tmp_path / "layers.json"
    fixture_pdf(source)
    layer_spec(spec)
    result = render_layers(source, spec, tmp_path / "output", combined=True)
    assert set(result["outputs"]) == {"ja", "en", "combined"}
    with fitz.open(source) as original:
        drawings = original[0].get_drawings()
        for language in ["ja", "en"]:
            with fitz.open(result["outputs"][language]) as doc:
                assert doc.page_count == 2
                assert doc[0].rect == original[0].rect
                assert len(doc[0].get_drawings()) == len(drawings)
                assert "SOURCE-MARKER" in doc[0].get_text()
                expected = {"ja": "こんばんは", "en": "Good evening"}
                assert expected[language] in doc[0].get_text()
                assert expected[{"ja": "en", "en": "ja"}[language]] not in doc[0].get_text()
        with fitz.open(result["outputs"]["combined"]) as doc:
            assert len(doc.get_ocgs()) == 2
            assert {item["name"] for item in doc.get_ocgs().values()} == {
                "GakufuLayer: ja", "GakufuLayer: en"
            }
            assert len(doc.get_layer()["rbgroups"]) == 1
            assert len(doc[0].get_drawings()) == len(drawings)


def test_reject_unreviewed_or_out_of_page(tmp_path):
    source = tmp_path / "synthetic.pdf"
    spec = tmp_path / "layers.json"
    fixture_pdf(source)
    layer_spec(spec)
    data = json.loads(spec.read_text())
    data["placements"][0]["status"] = "needs_review"
    spec.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="reviewed"):
        render_layers(source, spec, tmp_path / "out")
    data["placements"][0]["status"] = "reviewed"
    data["placements"][0]["rect"] = [480, 290, 600, 350]
    spec.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="outside page"):
        render_layers(source, spec, tmp_path / "out")


def test_rtl_requires_explicit_font(tmp_path):
    source = tmp_path / "synthetic.pdf"
    spec = tmp_path / "rtl.json"
    fixture_pdf(source)
    data = {
        "schema_version": "1.0",
        "source_language": "de",
        "placements": [
            {
                "source_ref": "seg-ar", "page": 1, "language": "ar",
                "text": "مرحبا بالعالم", "status": "reviewed",
                "reviewer": "arabic-reviewer", "rect": [25, 45, 350, 90],
            }
        ],
    }
    spec.write_text(json.dumps(data, ensure_ascii=False))
    with pytest.raises(ValueError, match="requires an explicit"):
        render_layers(source, spec, tmp_path / "out")


def test_rtl_with_font_extracts_unicode(tmp_path):
    if not shutil.which("fc-match"):
        pytest.skip("fontconfig not installed")
    font = subprocess.run(
        ["fc-match", "-f", "%{file}", "Noto Naskh Arabic"],
        check=True, capture_output=True, text=True
    ).stdout.strip()
    if not font or not Path(font).is_file() or "Arabic" not in Path(font).name:
        pytest.skip("Noto Arabic font not installed")
    source = tmp_path / "synthetic.pdf"
    spec = tmp_path / "rtl.json"
    fixture_pdf(source)
    expected = "مرحبا بالعالم"
    data = {
        "schema_version": "1.0",
        "source_language": "de",
        "placements": [
            {
                "source_ref": "seg-ar", "page": 1, "language": "ar",
                "text": expected, "status": "reviewed",
                "reviewer": "arabic-reviewer", "rect": [25, 45, 350, 95],
            }
        ],
    }
    spec.write_text(json.dumps(data, ensure_ascii=False))
    result = render_layers(
        source, spec, tmp_path / "out", font_map={"ar": font}
    )
    with fitz.open(result["outputs"]["ar"]) as doc:
        assert expected in unicodedata.normalize("NFKC", doc[0].get_text())


def test_fail_closed_when_text_does_not_fit(tmp_path):
    source = tmp_path / "synthetic.pdf"
    spec = tmp_path / "layers.json"
    fixture_pdf(source)
    layer_spec(spec, languages=("en",))
    data = json.loads(spec.read_text())
    data["placements"][0]["rect"] = [35, 45, 65, 50]
    spec.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="does not fit"):
        render_layers(source, spec, tmp_path / "output")
    assert list((tmp_path / "output").glob("*.pdf")) == []


def test_page_mapping_when_annotation_targets_second_page(tmp_path):
    source = tmp_path / "synthetic.pdf"
    spec = tmp_path / "layers.json"
    fixture_pdf(source)
    layer_spec(spec, languages=("en",))
    data = json.loads(spec.read_text())
    data["placements"][0]["page"] = 2
    spec.write_text(json.dumps(data))
    result = render_layers(source, spec, tmp_path / "output")
    with fitz.open(result["outputs"]["en"]) as doc:
        assert "Good evening" not in doc[0].get_text()
        assert "Good evening" in doc[1].get_text()
        assert doc[0].rect == doc[1].rect
