"""Command-line interface for GakufuLayer."""

from __future__ import annotations

import argparse

from gakufulayer.preprocess import split_pdf


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
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
