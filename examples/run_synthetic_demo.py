"""Run GakufuLayer's end-to-end synthetic score demonstration.

Only generated notation-like lines and short, reviewed example translations
are used. No third-party scores, lyrics, translations, or font files are bundled.
This script requires the opt-in [pdf] renderer and does not clear its licensing.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pymupdf as fitz

from create_synthetic_score import make_synthetic_score
from gakufulayer.blocks import assemble_blocks, remap_placements
from gakufulayer.pdf_metadata import audit_pdf_metadata
from gakufulayer.preprocess import split_pdf
from gakufulayer.overlay import render_layers


EXPECTED_TRANSLATIONS = {"ja": "こんばんは", "en": "Good evening"}


def run_demo(output_dir: str | Path) -> dict:
    destination = Path(output_dir).resolve()
    destination.mkdir(parents=True, exist_ok=True)
    source = destination / "synthetic-score.pdf"
    make_synthetic_score(source)

    block_dir = destination / "page-blocks"
    manifest = split_pdf(
        source, block_dir, start_page=1, end_page=1, block_size=1,
        source_language="de", target_languages=["ja", "en"],
    )
    if len(manifest["blocks"]) != 1:
        raise AssertionError("Synthetic demonstration should have exactly one block")

    assembled = destination / "selected.pdf"
    assembly_report = assemble_blocks(
        block_dir / "manifest.json", assembled, source_pdf=source,
    )
    if assembly_report["page_mapping"] != [{
        "source_page": 1, "output_page": 1,
        "block_file": "blocks/pages_0001-0001.pdf", "block_page": 1,
    }]:
        raise AssertionError("Unexpected source-to-output page mapping")

    assembly_json = destination / "page-map.json"
    assembly_json.write_text(
        json.dumps(assembly_report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    translated_spec = destination / "selected-placements.json"
    remap_placements(
        Path(__file__).with_name("placements.synthetic.json"),
        assembly_json,
        translated_spec,
    )
    rendering = render_layers(
        assembled, translated_spec, destination / "rendered", combined=True,
    )

    with fitz.open(source) as input_pdf:
        original_drawings = len(input_pdf[0].get_drawings())
        original_text = input_pdf[0].get_text()
    verification = {}
    for language, expected_text in EXPECTED_TRANSLATIONS.items():
        with fitz.open(rendering["outputs"][language]) as document:
            extracted = document[0].get_text()
            other_language = next(key for key in EXPECTED_TRANSLATIONS if key != language)
            if not (
                document.page_count == 1
                and expected_text in extracted
                and EXPECTED_TRANSLATIONS[other_language] not in extracted
                and "Guten Abend" in extracted
                and original_drawings == len(document[0].get_drawings())
                and all(word in extracted for word in ["GakufuLayer", "generated"])
            ):
                raise AssertionError(f"Source/vector/translation check failed: {language}")
            verification[language] = {
                "extracted_text_matches": True,
                "source_text_preserved": "Guten Abend" in extracted
                and "GakufuLayer" in extracted and "generated" in extracted,
                "notation_line_drawings_preserved": True,
                "page_count": document.page_count,
                "metadata_provenance": audit_pdf_metadata(
                    assembled, rendering["outputs"][language]
                )["status"],
            }

    with fitz.open(rendering["outputs"]["combined"]) as combined:
        layers = {group["name"] for group in combined.get_ocgs().values()}
        if layers != {"GakufuLayer: ja", "GakufuLayer: en"}:
            raise AssertionError(f"Unexpected optional content groups: {layers}")
        if len(combined[0].get_drawings()) != original_drawings:
            raise AssertionError("Notation-like source vectors were modified")
        combined_verification = {
            "layers": sorted(layers),
            "page_count": combined.page_count,
            "notation_line_drawings_preserved": True,
            "metadata_provenance": audit_pdf_metadata(
                assembled, rendering["outputs"]["combined"]
            )["status"],
        }

    if "Guten Abend" not in original_text:
        raise AssertionError("Original synthetic source text is missing")
    report = {
        "schema_version": "1.0",
        "fixture": "generated_synthetic_score_only",
        "real_score_tested": False,
        "translation": "manually_reviewed_example_text",
        "automatic_lyric_detection": False,
        "automatic_translation": False,
        "automatic_ipa": False,
        "automatic_placement": False,
        "page_mapping_verified": True,
        "languages": verification,
        "combined": combined_verification,
        "output_files": {
            name: str(Path(path).relative_to(destination))
            for name, path in rendering["outputs"].items()
        },
        "license_clearance": (
            "Not evaluated: PyMuPDF AGPL/commercial terms and "
            "distribution/hosted obligations require separate review."
        ),
        "status": "pass",
    }
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir", default="build/synthetic-demo",
        help="Local output directory for generated artifacts",
    )
    parser.add_argument("--report", help="JSON report path (default: output_dir/demo-report.json)")
    args = parser.parse_args(argv)
    report = run_demo(args.output_dir)
    report_path = (
        Path(args.report) if args.report else Path(args.output_dir) / "demo-report.json"
    )
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "status": report["status"],
        "languages": sorted(report["languages"]),
        "source_vectors_preserved": report["combined"]["notation_line_drawings_preserved"],
        "report": str(report_path),
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
