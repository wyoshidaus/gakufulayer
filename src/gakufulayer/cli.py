"""Command-line interface for GakufuLayer."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from gakufulayer.preprocess import split_pdf
from gakufulayer.overlay import render_layers
from gakufulayer.translation_commit import commit_translation


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="gakufulayer")
    commands = parser.add_subparsers(dest="command", required=True)
    preprocess = commands.add_parser("preprocess", help="Split a PDF into page blocks")
    preprocess.add_argument("input_pdf")
    preprocess.add_argument("--output-dir", required=True)
    preprocess.add_argument("--start-page", type=int, default=1)
    preprocess.add_argument("--end-page", type=int)
    preprocess.add_argument("--block-size", type=int, default=10)
    preprocess.add_argument("--source-language", help="Source lyric language (e.g. de)")
    preprocess.add_argument(
        "--target-language",
        action="append",
        dest="target_languages",
        metavar="LANG",
        help="Target language (repeat for multiple targets; e.g. ja and en)",
    )
    commit = commands.add_parser(
        "commit-translation",
        help="Validate and commit one line-oriented translation unit",
    )
    commit.add_argument("ready_file")
    commit.add_argument("translation_output")
    commit.add_argument("passed_output")
    commit.add_argument("--source-language", required=True)
    commit.add_argument("--target-language", required=True)
    commit.add_argument("--overwrite", action="store_true")

    render = commands.add_parser(
        "render",
        help="Render reviewed translation placements as independent PDF text layers",
    )
    render.add_argument("input_pdf")
    render.add_argument("placements_json")
    render.add_argument("--output-dir", required=True)
    render.add_argument("--combined", action="store_true",
                        help="Also produce a PDF with switchable language layers")
    render.add_argument("--font", action="append", default=[], metavar="LANG=PATH",
                        help="Embed a local font for one target language; repeat as needed")
    render.add_argument("--report", help="Optional JSON execution report path")

    args = parser.parse_args(argv)

    if args.command == "preprocess":
        try:
            manifest = split_pdf(
                args.input_pdf,
                args.output_dir,
                start_page=args.start_page,
                end_page=args.end_page,
                block_size=args.block_size,
                source_language=args.source_language,
                target_languages=args.target_languages,
            )
        except (FileNotFoundError, ValueError) as exc:
            parser.error(str(exc))
        print(
            f"Created {len(manifest['blocks'])} block(s) "
            f"for pages {manifest['start_page']}–{manifest['end_page']}"
        )
        return 0

    if args.command == "commit-translation":
        try:
            result = commit_translation(
                Path(args.ready_file),
                Path(args.translation_output),
                Path(args.passed_output),
                source_language=args.source_language,
                target_language=args.target_language,
                overwrite=args.overwrite,
            )
        except (FileNotFoundError, ValueError) as exc:
            parser.error(str(exc))
        print(result["status"])
        return 0 if result["status"] in {"passed", "already_committed"} else 2

    if args.command == "render":
        fonts: dict[str, str] = {}
        try:
            for mapping in args.font:
                language, sep, filename = mapping.partition("=")
                if not sep or not language.strip() or not filename.strip():
                    raise ValueError("--font must use LANG=/path/to/font.ttf")
                fonts[language] = filename
            report = render_layers(
                args.input_pdf,
                args.placements_json,
                args.output_dir,
                font_map=fonts,
                combined=args.combined,
            )
        except (OSError, ValueError) as exc:
            parser.error(str(exc))
        if args.report:
            path = Path(args.report)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                json.dumps(report, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
        print(json.dumps(report, ensure_ascii=False))
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
