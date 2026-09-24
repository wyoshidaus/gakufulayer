"""Synthetic dependency inventory tests. No external wheel downloads required."""

from __future__ import annotations

from email.message import Message
from pathlib import Path, PurePosixPath

from scripts.dependency_inventory import canonical_name, collect_inventory


class FakeDistribution:
    def __init__(self, root: Path, name: str, version: str, license_value: str | None,
                 *, marker_field: str = "License-Expression",
                 with_notice: bool = True) -> None:
        self.root = root
        self.version = version
        self.metadata = Message()
        self.metadata["Name"] = name
        if license_value is not None:
            self.metadata[marker_field] = license_value
        self.metadata["Requires-Dist"] = "pypdf>=5"
        self.requires = ["pypdf>=5"]
        self._relative = f"{name}-{version}.dist-info/licenses/LICENSE"
        self.files = [PurePosixPath(self._relative)] if with_notice else []
        if with_notice:
            path = root / self._relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(f"DELIBERATELY SYNTHETIC LICENSE TEXT FOR {name}", encoding="utf-8")

    def locate_file(self, relative):
        return self.root / relative


def test_normalization_deduplicates_editable_distribution_and_copies_notices(tmp_path):
    pypdf = FakeDistribution(tmp_path, "py_pdf", "6.19", "BSD-3-Clause")
    result = collect_inventory(
        [pypdf, pypdf], mode="core", notice_dir=tmp_path / "notices",
    )
    assert canonical_name("Py_PDF") == "py-pdf"
    # Core requires exactly the pypdf package name, not a lookalike.
    assert result["environment_errors"] == ["pypdf_missing"]
    pypdf = FakeDistribution(tmp_path, "pypdf", "6.19", "BSD-3-Clause")
    result = collect_inventory(
        [pypdf, pypdf], mode="core", notice_dir=tmp_path / "notices",
    )
    assert result["environment_errors"] == []
    assert len(result["packages"]) == 1
    item = result["packages"][0]
    assert item["normalized_name"] == "pypdf"
    assert item["license_markers"] == ["BSD-3-Clause"]
    assert item["requires_dist"] == ["pypdf>=5"]
    assert len(item["license_files"]) == 1
    evidence = item["license_files"][0]
    assert len(evidence["sha256"]) == 64
    assert (tmp_path / "notices" / evidence["evidence_path"]).is_file()
    assert not result["release_cleared"]


def test_optional_agpl_dependency_requires_explicit_approval(tmp_path):
    pypdf = FakeDistribution(tmp_path, "pypdf", "6", "BSD-3-Clause")
    renderer = FakeDistribution(
        tmp_path, "PyMuPDF", "1.28.2",
        "Dual Licensed - GNU AFFERO GPL 3.0 or Artifex Commercial License",
        marker_field="License",
    )
    base = collect_inventory([pypdf, renderer], mode="core")
    assert "PyMuPDF_must_not_be_in_core_install" in base["environment_errors"]
    full = collect_inventory([pypdf, renderer], mode="full")
    assert full["environment_errors"] == []
    assert {
        (r["package"], r["reason"]) for r in full["review_required"]
    } >= {
        ("pymupdf", "AGPLv3_or_commercial_licensing_route_requires_manual_decision")
    }
    assert full["release_cleared"] is False


def test_missing_license_marker_and_missing_text_are_review_flags(tmp_path):
    pypdf = FakeDistribution(tmp_path, "pypdf", "6", "BSD-3-Clause")
    unknown = FakeDistribution(
        tmp_path, "buildhelper", "1.0", None, with_notice=False
    )
    result = collect_inventory([pypdf, unknown], mode="core")
    assert ("buildhelper", "license_expression_unknown") in {
        (r["package"], r["reason"]) for r in result["review_required"]
    }
    assert ("buildhelper", "bundled_license_text_not_found") in {
        (r["package"], r["reason"]) for r in result["review_required"]
    }


def test_full_install_without_renderer_is_environment_error(tmp_path):
    pypdf = FakeDistribution(tmp_path, "pypdf", "6", "BSD-3-Clause")
    report = collect_inventory([pypdf], mode="full")
    assert report["environment_errors"] == ["PyMuPDF_missing_from_full_install"]


def test_duplicate_editable_metadata_does_not_raise_false_missing_notice(tmp_path):
    good = FakeDistribution(tmp_path / "good", "pypdf", "6.19", "BSD-3-Clause")
    broken = FakeDistribution(tmp_path / "broken", "pypdf", "6.19", "BSD-3-Clause")
    missing = broken.root / broken._relative
    missing.unlink()
    result = collect_inventory([broken, good], mode="core")
    assert len(result["packages"]) == 1
    assert result["packages"][0]["evidence_warnings"] == []
    assert result["review_required"] == []
