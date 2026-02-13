"""Command-line interface for notion-markdown."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from notion_markdown import __version__, to_markdown, to_notion


def _add_io_args(parser: argparse.ArgumentParser) -> None:
    """Add common input/output arguments shared across subcommands."""
    parser.add_argument(
        "file",
        nargs="?",
        type=Path,
        default=None,
        help="Input file (reads from stdin if omitted)",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="Write output to a file (prints to stdout if omitted)",
    )


def _read_input(args: argparse.Namespace, parser: argparse.ArgumentParser) -> str:
    """Read input from file argument or stdin."""
    if args.file is not None:
        filepath: Path = args.file
        return filepath.read_text(encoding="utf-8")
    if not sys.stdin.isatty():
        return sys.stdin.read()
    parser.error("no input provided — pass a file or pipe via stdin")
    raise SystemExit(2)  # pragma: no cover — unreachable; parser.error always exits


def _write_output(text: str, output: Path | None) -> None:
    """Write text to a file or stdout."""
    if output is not None:
        output.write_text(text, encoding="utf-8")
    else:
        sys.stdout.write(text)


def _cmd_to_notion(args: argparse.Namespace, parser: argparse.ArgumentParser) -> None:
    """Convert Markdown to Notion API JSON blocks."""
    markdown = _read_input(args, parser)
    blocks = to_notion(markdown)
    indent = args.indent if args.indent > 0 else None
    output = json.dumps(blocks, indent=indent, ensure_ascii=False) + "\n"
    _write_output(output, args.output)


def _cmd_to_markdown(args: argparse.Namespace, parser: argparse.ArgumentParser) -> None:
    """Convert Notion API JSON blocks to Markdown."""
    raw = _read_input(args, parser)
    blocks = json.loads(raw)
    if not isinstance(blocks, list):
        parser.error("input must be a JSON array of Notion blocks")
    output = to_markdown(blocks)
    _write_output(output, args.output)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="notion-markdown",
        description="Convert between Markdown and Notion API block objects.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )

    subparsers = parser.add_subparsers(dest="command")

    # --- to-notion --------------------------------------------------------
    to_notion = subparsers.add_parser(
        "to-notion",
        help="Convert Markdown to Notion API JSON blocks",
        description="Convert Markdown to Notion API JSON blocks.",
    )
    _add_io_args(to_notion)
    to_notion.add_argument(
        "--indent",
        type=int,
        default=2,
        help="JSON indentation level (default: 2, use 0 for compact)",
    )

    # --- to-markdown (placeholder) ----------------------------------------
    to_markdown = subparsers.add_parser(
        "to-markdown",
        help="Convert Notion API JSON blocks to Markdown",
        description="Convert Notion API JSON blocks to Markdown.",
    )
    _add_io_args(to_markdown)

    return parser


def main(argv: list[str] | None = None) -> None:
    """Entry point for the CLI."""
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command == "to-notion":
        _cmd_to_notion(args, parser)
    elif args.command == "to-markdown":
        _cmd_to_markdown(args, parser)
    else:
        parser.print_help()
        sys.exit(2)


if __name__ == "__main__":  # pragma: no cover
    main()
