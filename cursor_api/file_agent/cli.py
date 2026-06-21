"""CLI для file_agent."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def _resolve_source_path(file_arg: str) -> Path:
    path = Path(file_arg).expanduser()
    if path.is_absolute():
        return path.resolve()

    # README documents repo-root relative paths even when the command runs from cursor_api.
    return (REPO_ROOT / path).resolve()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="file_agent",
        description="Локальный пайплайн перевода больших текстовых файлов через Cursor Agent (composer-2.5).",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    run = sub.add_parser(
        "run",
        help="Перевести файл (-t) или собрать части обратно (-merge)",
    )
    run.add_argument(
        "file",
        metavar="FILE",
        help="Путь к исходному файлу",
    )
    mode = run.add_mutually_exclusive_group(required=True)
    mode.add_argument(
        "-t",
        metavar="STORY_CONTEXT",
        help=(
            "Нормализовать, разбить и перевести части. STORY_CONTEXT — "
            "английское ASCII-описание истории, персонажей и их пола."
        ),
    )
    mode.add_argument(
        "-merge",
        action="store_true",
        help="Собрать исходный файл и части S001, S002, ... в исходный FILE",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

    args = build_parser().parse_args(argv)

    if args.command == "run":
        source = _resolve_source_path(args.file)
        from file_agent import pipeline

        if args.t is not None:
            return pipeline.run_translate(source, args.t)
        return pipeline.run_merge(source)

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
