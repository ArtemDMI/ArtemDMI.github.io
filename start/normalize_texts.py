from __future__ import annotations

import argparse
import sys
import unicodedata
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
CURSOR_API_DIR = PROJECT_ROOT / "cursor_api"

# Reuse the existing pipeline normalization so manual batch cleanup stays
# aligned with the translation flow and does not drift into a separate format.
sys.path.insert(0, str(CURSOR_API_DIR))

from file_agent.normalization import normalize_text


def remove_square_brackets(text: str) -> str:
    result: list[str] = []
    depth = 0

    for char in text:
        if char == "[":
            depth += 1
            continue
        if char == "]":
            if depth > 0:
                depth -= 1
                continue
        if depth == 0:
            result.append(char)

    return "".join(result)


def strip_non_text_symbols(text: str) -> str:
    cleaned: list[str] = []

    for char in text:
        if char in "\r\n\t":
            cleaned.append(char)
            continue

        category = unicodedata.category(char)
        if category[0] in {"L", "M", "N", "P"}:
            cleaned.append(char)
            continue
        if category == "Zs":
            cleaned.append(" ")
            continue

        # Replace visual noise like music notes with spaces so neighboring
        # words do not merge before sentence normalization runs.
        cleaned.append(" ")

    return "".join(cleaned)


def preprocess_text(text: str) -> str:
    return strip_non_text_symbols(remove_square_brackets(text))


def normalize_file(path: Path) -> bool:
    original = path.read_text(encoding="utf-8")
    normalized = normalize_text(preprocess_text(original)) + "\n"

    if original == normalized:
        return False

    path.write_text(normalized, encoding="utf-8")
    return True


def iter_txt_files(paths: list[str], recursive: bool) -> list[Path]:
    collected: list[Path] = []
    seen: set[Path] = set()

    for raw_path in paths:
        path = Path(raw_path).expanduser().resolve()
        if not path.exists():
            raise FileNotFoundError(f"Path not found: {path}")

        if path.is_file():
            if path.suffix.lower() == ".txt" and path not in seen:
                collected.append(path)
                seen.add(path)
            continue

        pattern = "**/*.txt" if recursive else "*.txt"
        for file_path in sorted(path.glob(pattern)):
            if file_path.is_file() and file_path not in seen:
                collected.append(file_path)
                seen.add(file_path)

    return collected


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Remove bracketed fragments and symbol noise, then run the same "
            "text normalization as cursor_api/file_agent."
        )
    )
    parser.add_argument(
        "paths",
        nargs="+",
        help="One or more .txt files or directories with .txt files.",
    )
    parser.add_argument(
        "--recursive",
        action="store_true",
        help="When a directory is passed, include .txt files from subfolders too.",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    try:
        files = iter_txt_files(args.paths, recursive=args.recursive)
    except FileNotFoundError as error:
        print(f"[ERROR] {error}")
        return 1

    if not files:
        print("[ERROR] No .txt files found.")
        return 1

    changed = 0
    failed = 0

    for path in files:
        try:
            if normalize_file(path):
                changed += 1
                print(f"[CHANGED] {path}")
            else:
                print(f"[UNCHANGED] {path}")
        except Exception as error:
            failed += 1
            print(f"[ERROR] {path}: {error}")

    print(
        f"[DONE] files={len(files)} changed={changed} unchanged={len(files) - changed - failed} failed={failed}"
    )
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
