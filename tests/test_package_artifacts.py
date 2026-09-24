"""Check the package-preflight checker with minimal synthetic archives."""

from __future__ import annotations

import io
import tarfile
import zipfile

import pytest

from scripts.check_package_artifacts import check_distributions


LICENSE = b"INTENTIONALLY SYNTHETIC LICENSE TEXT FOR PACKAGING TESTS\n"


def synthetic_archives(tmp_path, *, license_expression="Apache-2.0",
                       pdf_marker='; extra == "pdf"', include_license=True):
    wheel = tmp_path / "gakufulayer-0.1.0.dev0-py3-none-any.whl"
    sdist = tmp_path / "gakufulayer-0.1.0.dev0.tar.gz"
    root = tmp_path / "LICENSE"
    root.write_bytes(LICENSE)
    meta = (
        "Metadata-Version: 2.4\n"
        "Name: gakufulayer\n"
        "Version: 0.1.0.dev0\n"
        f"License-Expression: {license_expression}\n"
        "License-File: LICENSE\n"
        "Requires-Dist: pypdf<7,>=5\n"
        f"Requires-Dist: PyMuPDF<2,>=1.26{pdf_marker}\n"
        '\n'
    )
    with zipfile.ZipFile(wheel, "w") as output:
        output.writestr("gakufulayer-0.1.0.dev0.dist-info/METADATA", meta)
        if include_license:
            output.writestr("gakufulayer-0.1.0.dev0.dist-info/licenses/LICENSE", LICENSE)
    with tarfile.open(sdist, "w:gz") as output:
        info = tarfile.TarInfo("gakufulayer-0.1.0.dev0/LICENSE")
        info.size = len(LICENSE)
        output.addfile(info, io.BytesIO(LICENSE))
    return wheel, sdist, root


def test_package_gate_recognizes_opt_in_pdf_backend(tmp_path):
    wheel, sdist, license_file = synthetic_archives(tmp_path)
    result = check_distributions(wheel, sdist, license_file)
    assert result["packaging_status"] == "pass"
    assert result["unconditional_dependencies"] == ["pypdf"]
    assert result["optional_dependencies"]["pdf"] == ["pymupdf"]
    assert result["release_cleared"] is False
    assert len(result["checks"]) == 4


@pytest.mark.parametrize(
    "variant,message", [
        ({"license_expression": "MIT"}, "License-Expression"),
        ({"pdf_marker": ""}, "PyMuPDF must not be an unconditional"),
        ({"include_license": False}, "wheel bundled LICENSE"),
    ],
)
def test_package_gate_rejects_bad_artifacts(tmp_path, variant, message):
    wheel, sdist, license_file = synthetic_archives(tmp_path, **variant)
    with pytest.raises(ValueError, match=message):
        check_distributions(wheel, sdist, license_file)
