"""Command-line interface for GakufuLayer."""

from __future__ import annotations

import argparse
from pathlib import Path

from gakufulayer.preprocess import split_pdf
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

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
