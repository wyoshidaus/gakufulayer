"""Generate a synthetic score-like PDF for demos; contains no third-party score."""
from __future__ import annotations

import argparse
from pathlib import Path

import pymupdf as fitz


def make_synthetic_score(path: str | Path) -> None:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with fitz.open() as pdf:
        page = pdf.new_page(width=595, height=842)
        page.insert_text((75, 110), "GakufuLayer: generated demonstration page", fontsize=12)
        page.draw_line((60, 280), (535, 280), width=1)
        for line in range(5):
            page.draw_line((60, 340 + line * 12), (535, 340 + line * 12), width=0.8)
        page.insert_text((80, 330), "Guten Abend", fontsize=11)
        pdf.save(destination)


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a rights-safe synthetic demonstration PDF")
    parser.add_argument("output_pdf", nargs="?", default="synthetic-score.pdf")
    args = parser.parse_args()
    make_synthetic_score(args.output_pdf)


if __name__ == "__main__":
    main()
