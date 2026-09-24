"""Conservative /Info and XMP provenance audit for PDF transformations.

This module intentionally uses the core pypdf dependency; it does not make
PyMuPDF a requirement for inspecting PDF metadata.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pypdf import PdfReader, PdfWriter
from pypdf.generic import DecodedStreamObject, NameObject

# Dates may legitimately change when a new PDF is written; they are reported
# separately in the future if release review needs them.
_MUTABLE_INFO_KEYS = frozenset({"/CreationDate", "/ModDate"})


def _metadata_snapshot(path: str | Path) -> tuple[dict[str, str], bytes]:
    reader = PdfReader(str(path))
    if reader.is_encrypted:
        raise ValueError(f"Cannot audit encrypted PDF metadata: {path}")
    info = {
        str(key): str(value)
        for key, value in (reader.metadata or {}).items()
        if value is not None and str(value).strip()
    }
    xmp_ref = reader.trailer["/Root"].get("/Metadata")
    xml_bytes = xmp_ref.get_object().get_data() if xmp_ref is not None else b""
    return info, xml_bytes


def copy_source_metadata(source: PdfReader, destination: PdfWriter) -> dict[str, Any]:
    """Copy original PDF Info and XMP to a new PDF writer without flattening pages.

    pypdf has public add_metadata for PDF Info but no public root-XMP setter
    across the supported versions. The small catalog write below is covered
    by synthetic round-trip tests in the supported Python CI matrix.
    """
    if source.is_encrypted:
        raise ValueError("Cannot copy metadata from encrypted source PDF")
    values = {
        str(key): str(value)
        for key, value in (source.metadata or {}).items()
        if value is not None
    }
    if values:
        destination.add_metadata(values)
    original_xmp = source.trailer["/Root"].get("/Metadata")
    if original_xmp is not None:
        xmp_stream = DecodedStreamObject()
        xmp_stream.set_data(original_xmp.get_object().get_data())
        xmp_stream.update({
            NameObject("/Type"): NameObject("/Metadata"),
            NameObject("/Subtype"): NameObject("/XML"),
        })
        destination._root_object[NameObject("/Metadata")] = destination._add_object(xmp_stream)
    return {"copied_info_fields": sorted(values), "copied_xmp": original_xmp is not None}


def audit_pdf_metadata(
    source_pdf: str | Path,
    output_pdf: str | Path,
) -> dict[str, Any]:
    """Detect loss of source /Info notices and XMP; flag absent producer.

    Status values: pass, review_required, fail. This compares retained
    source metadata; it does NOT certify AGPL compliance, font rights or
    generated-PDF notice sufficiency for a particular distribution model.
    """
    before_info, before_xmp = _metadata_snapshot(source_pdf)
    after_info, after_xmp = _metadata_snapshot(output_pdf)
    checks: list[dict[str, str]] = []
    for field in sorted(before_info):
        if field in _MUTABLE_INFO_KEYS:
            continue
        retained = after_info.get(field) == before_info[field]
        checks.append({
            "field": field,
            "status": "pass" if retained else "fail",
            "reason": "source_info_preserved" if retained else "source_info_changed_or_missing",
        })

    if before_xmp:
        retained = before_xmp == after_xmp
        checks.append({
            "field": "XMP",
            "status": "pass" if retained else "fail",
            "reason": "source_xmp_preserved" if retained else "source_xmp_changed_or_missing",
        })
    elif after_xmp:
        checks.append({
            "field": "XMP",
            "status": "pass",
            "reason": "xmp_added_to_source_without_xmp",
        })
    else:
        checks.append({
            "field": "XMP",
            "status": "not_applicable",
            "reason": "source_did_not_contain_xmp",
        })

    if not after_info.get("/Producer"):
        checks.append({
            "field": "/Producer",
            "status": "warning",
            "reason": "output_has_no_producer_notice_manual_review_required",
        })

    status = (
        "fail" if any(c["status"] == "fail" for c in checks)
        else "review_required" if any(c["status"] == "warning" for c in checks)
        else "pass"
    )
    return {
        "status": status,
        "source_pdf": str(Path(source_pdf)),
        "output_pdf": str(Path(output_pdf)),
        "source_info_fields": sorted(before_info),
        "output_info_fields": sorted(after_info),
        "source_has_xmp": bool(before_xmp),
        "output_has_xmp": bool(after_xmp),
        "checks": checks,
        "limits": (
            "Conservative source metadata preservation audit; not proof "
            "of license compliance or producer-notice sufficiency."
        ),
    }


def save_audit_report(path: str | Path, report: dict[str, Any]) -> None:
    """Write a report without copying original personal/rights text values."""
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
