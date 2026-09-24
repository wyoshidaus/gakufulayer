"""Preserve score PDF content while adding reviewed, language-specific text layers.

This intentionally consumes pre-aligned rectangles. Automatic lyric extraction,
translation, collision avoidance, and automatic font acquisition are out of scope.
"""
from __future__ import annotations

import html
import json
import math
import os
import tempfile
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

import fitz

from gakufulayer.languages import normalize_language_tag
from gakufulayer.pdf_metadata import audit_pdf_metadata

RTL_LANGUAGES = frozenset({"ar", "fa", "he", "ur", "ps", "sd"})


def _normalized_text(text: str) -> str:
    """Normalize typographic forms and whitespace for extraction checks."""
    return " ".join(unicodedata.normalize("NFKC", text).split())


@dataclass(frozen=True)
class Placement:
    source_ref: str
    page: int
    language: str
    text: str
    rect: tuple[float, float, float, float]
    reviewer: str
    font_size: float = 9.0
    min_font_size: float = 6.0
    color: tuple[float, float, float] = (0.78, 0.08, 0.12)

    @classmethod
    def from_dict(cls, item: Mapping[str, Any]) -> "Placement":
        if item.get("status") != "reviewed" or not str(item.get("reviewer", "")).strip():
            raise ValueError("Only reviewed placements with reviewer metadata can be rendered")
        try:
            raw_rect = item["rect"]
            if not isinstance(raw_rect, (list, tuple)) or len(raw_rect) != 4:
                raise ValueError("rect must contain [x0, y0, x1, y1]")
            rect = tuple(float(x) for x in raw_rect)
            raw_color = item.get("color", [0.78, 0.08, 0.12])
            if not isinstance(raw_color, (list, tuple)) or len(raw_color) != 3:
                raise ValueError("color must contain three floats")
            color = tuple(float(x) for x in raw_color)
            placement = cls(
                source_ref=str(item["source_ref"]).strip(),
                page=int(item["page"]),
                language=normalize_language_tag(str(item["language"])),
                text=str(item["text"]),
                rect=rect,
                reviewer=str(item["reviewer"]).strip(),
                font_size=float(item.get("font_size", 9)),
                min_font_size=float(item.get("min_font_size", 6)),
                color=color,
            )
        except (KeyError, TypeError, OverflowError) as exc:
            raise ValueError(f"Invalid placement: {exc}") from exc
        if not placement.source_ref or not placement.text.strip():
            raise ValueError("source_ref and text must not be empty")
        if placement.page < 1:
            raise ValueError("page must be 1 or greater")
        if not all(math.isfinite(v) for v in (*placement.rect, *placement.color)):
            raise ValueError("rect and color must have finite numbers")
        x0, y0, x1, y1 = placement.rect
        if x1 <= x0 or y1 <= y0:
            raise ValueError("rect width and height must be positive")
        if any(c < 0 or c > 1 for c in placement.color):
            raise ValueError("color must contain RGB numbers in [0, 1]")
        if not 0 < placement.min_font_size <= placement.font_size <= 72:
            raise ValueError("font sizes must satisfy 0 < minimum <= preferred <= 72")
        return placement


def load_placements(spec_path: str | Path) -> tuple[str, list[Placement]]:
    raw = json.loads(Path(spec_path).read_text(encoding="utf-8"))
    if raw.get("schema_version") != "1.0":
        raise ValueError("Expected placement schema_version 1.0")
    source_language = normalize_language_tag(str(raw["source_language"]))
    items = raw.get("placements")
    if not isinstance(items, list) or not items:
        raise ValueError("placements must be a non-empty list")
    placements = [Placement.from_dict(item) for item in items]
    if any(item.language == source_language for item in placements):
        raise ValueError("Translation language must differ from source language")
    return source_language, placements


def _is_rtl(language: str) -> bool:
    parts = language.split("-")
    return parts[0] in RTL_LANGUAGES or "Arab" in parts or "Hebr" in parts


def _validate_page_placements(doc: fitz.Document, placements: list[Placement]) -> None:
    seen: set[tuple[int, str, str]] = set()
    rects: dict[tuple[int, str], list[fitz.Rect]] = {}
    for item in placements:
        if item.page > doc.page_count:
            raise ValueError(f"Placement {item.source_ref}: page {item.page} out of range")
        rect = fitz.Rect(*item.rect)
        if not doc[item.page - 1].rect.contains(rect):
            raise ValueError(f"Placement {item.source_ref}: rectangle outside page bounds")
        key = (item.page, item.language, item.source_ref)
        if key in seen:
            raise ValueError(f"Duplicate placement {key}")
        seen.add(key)
        page_language = (item.page, item.language)
        if any(rect.intersects(existing) for existing in rects.get(page_language, [])):
            raise ValueError(
                f"Overlapping translation rectangles on page {item.page} for {item.language}"
            )
        rects.setdefault(page_language, []).append(rect)


def _insert_placement(
    page: fitz.Page,
    item: Placement,
    font_map: Mapping[str, str | Path],
    ocg: int = 0,
) -> float:
    """Insert selectable Unicode HTML text; use shaping for complex scripts."""
    primary = item.language.split("-")[0]
    selected_font = font_map.get(item.language) or font_map.get(primary)
    archive = None
    font_css = ""
    if selected_font is not None:
        font_path = Path(selected_font)
        if not font_path.is_file():
            raise FileNotFoundError(f"Font for {item.language} not found: {font_path}")
        archive = fitz.Archive()
        extension = font_path.suffix.lower()
        if extension not in {".ttf", ".otf"}:
            raise ValueError("Explicit fonts must use .ttf or .otf for HTML shaping")
        archive.add(font_path.read_bytes(), path=f"GakufuFont{extension}")
        font_css = (
            "@font-face {font-family:GakufuFont;"
            f"src:url(GakufuFont{extension});}}"
            "div {font-family:GakufuFont;}"
        )
    elif _is_rtl(item.language):
        raise ValueError(
            f"RTL language {item.language} requires an explicit, tested --font mapping"
        )
    direction = "rtl" if _is_rtl(item.language) else "ltr"
    color = tuple(round(c * 255) for c in item.color)
    safe_text = html.escape(item.text).replace("\n", "<br/>")
    tag = (
        f'<div dir="{direction}" lang="{html.escape(item.language)}">'
        f"{safe_text}</div>"
    )
    rect = fitz.Rect(*item.rect)
    font_size = item.font_size
    while font_size >= item.min_font_size - 1e-6:
        css = (
            font_css
            + "div {margin:0; padding:0; line-height:1.1; "
            f"font-size:{font_size:.2f}pt; "
            f"color:rgb({color[0]}, {color[1]}, {color[2]}); "
            f"text-align:{'right' if direction == 'rtl' else 'left'};}}"
        )
        spare_height, scale = page.insert_htmlbox(
            rect, tag, css=css, archive=archive, scale_low=1, oc=ocg, overlay=True
        )
        if spare_height >= 0 and scale == 1:
            return font_size
        font_size = round(font_size - 0.5, 2)
    raise ValueError(
        f"Placement {item.source_ref} ({item.language}): text does not fit above "
        f"minimum font size {item.min_font_size}"
    )


def _verify_output(doc: fitz.Document, placements: list[Placement]) -> None:
    for item in placements:
        text = _normalized_text(doc[item.page - 1].get_text())
        expected = _normalized_text(item.text)
        if expected not in text:
            raise ValueError(
                f"Placement {item.source_ref} ({item.language}): "
                "text extraction mismatch; check font/script configuration"
            )


def render_layers(
    source_pdf: str | Path,
    spec_path: str | Path,
    output_dir: str | Path,
    *,
    font_map: Mapping[str, str | Path] | None = None,
    combined: bool = False,
) -> dict[str, Any]:
    """Export separate target PDFs and optionally an OCG-toggleable combined PDF.

    Outputs are staged and published only after every output passes checks.
    Source pages remain vector PDF content; existing notation is not rasterized.
    """
    source = Path(source_pdf)
    if not source.is_file():
        raise FileNotFoundError(f"PDF not found: {source}")
    source_language, placements = load_placements(spec_path)
    font_map = {
        normalize_language_tag(tag): path for tag, path in (font_map or {}).items()
    }
    languages = list(dict.fromkeys(item.language for item in placements))
    result_dir = Path(output_dir)
    result_dir.mkdir(parents=True, exist_ok=True)
    with fitz.open(source) as original:
        if not original.is_pdf or original.needs_pass:
            raise ValueError("Input must be an accessible, unencrypted PDF")
        _validate_page_placements(original, placements)
        page_count = original.page_count
    reports: dict[str, Any] = {}
    with tempfile.TemporaryDirectory(dir=result_dir, prefix=".gakufulayer-") as staging:
        stage = Path(staging)
        names: dict[str, str] = {}
        for language in languages:
            subset = [item for item in placements if item.language == language]
            filename = f"{source.stem}.{language}.pdf"
            with fitz.open(source) as doc:
                for item in subset:
                    _insert_placement(doc[item.page - 1], item, font_map)
                _verify_output(doc, subset)
                doc.save(stage / filename, garbage=3, deflate=True)
            names[language] = filename
            reports[language] = len(subset)
        if combined:
            filename = f"{source.stem}.multilingual.pdf"
            with fitz.open(source) as doc:
                ocgs = {
                    language: doc.add_ocg(f"GakufuLayer: {language}", on=(i == 0))
                    for i, language in enumerate(languages)
                }
                if len(ocgs) > 1:
                    ids = list(ocgs.values())
                    doc.set_layer(-1, on=ids[:1], off=ids[1:], rbgroups=[ids])
                for item in placements:
                    _insert_placement(doc[item.page - 1], item, font_map, ocg=ocgs[item.language])
                _verify_output(doc, placements)
                doc.save(stage / filename, garbage=3, deflate=True)
            names["combined"] = filename
        # Verify the staged files before publishing any output. Record warning
        # states for human review, but block missing/modified source notices.
        metadata_audit: dict[str, dict[str, Any]] = {}
        for tag, filename in names.items():
            with fitz.open(stage / filename) as output:
                if output.page_count != page_count:
                    raise ValueError(f"Page count changed in {filename}")
            audit = audit_pdf_metadata(source, stage / filename)
            metadata_audit[tag] = {
                "status": audit["status"],
                "checks": audit["checks"],
                "source_has_xmp": audit["source_has_xmp"],
                "output_has_xmp": audit["output_has_xmp"],
                "limits": audit["limits"],
            }
            if audit["status"] == "fail":
                raise ValueError(
                    f"Metadata provenance audit failed in {filename}; "
                    "source /Info or XMP changed or disappeared"
                )
        for filename in names.values():
            os.replace(stage / filename, result_dir / filename)
    return {
        "source_language": source_language,
        "languages": languages,
        "page_count": page_count,
        "annotation_count": len(placements),
        "per_language": reports,
        "metadata_audit": metadata_audit,
        "outputs": {tag: str(result_dir / name) for tag, name in names.items()},
    }
