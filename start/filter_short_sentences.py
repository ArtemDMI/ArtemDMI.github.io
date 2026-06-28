from __future__ import annotations

import argparse
import re
import unicodedata
from pathlib import Path


SUBTITLE_TIMING_RE = re.compile(
    r"^\s*(?:\d{1,2}:)?\d{2}:\d{2}[,.]\d{1,3}\s*-->\s*"
    r"(?:\d{1,2}:)?\d{2}:\d{2}[,.]\d{1,3}(?:\s+.*)?$"
)
SUBTITLE_INDEX_RE = re.compile(r"^\s*\d+\s*$")
WORD_RE = re.compile(r"[^\W\d_]+(?:[-'][^\W\d_]+)*", flags=re.UNICODE)
MOJIBAKE_HINT_RE = re.compile(r"[╨╤]")


def is_subtitle_timing_line(line: str) -> bool:
    return bool(SUBTITLE_TIMING_RE.fullmatch(line))


def is_subtitle_index_line(line: str) -> bool:
    return bool(SUBTITLE_INDEX_RE.fullmatch(line))


def looks_like_subtitle(text: str) -> bool:
    return any(is_subtitle_timing_line(line) for line in text.splitlines())


def strip_subtitle_metadata(text: str) -> str:
    cleaned: list[str] = []

    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        if is_subtitle_index_line(line) or is_subtitle_timing_line(line):
            continue
        cleaned.append(line)

    return "\n".join(cleaned)


def text_quality_score(text: str) -> int:
    score = 0

    for char in text:
        category = unicodedata.category(char)
        if "А" <= char <= "я" or char in {"Ё", "ё"}:
            score += 4
        elif category[0] in {"L", "N"}:
            score += 2
        elif category[0] == "P" or char.isspace():
            score += 1
        elif MOJIBAKE_HINT_RE.fullmatch(char):
            score -= 6
        elif category[0] == "C":
            score -= 4
        else:
            score -= 2

    return score


def repair_mojibake(text: str) -> str:
    best_text = text
    best_score = text_quality_score(text)

    # If UTF-8 bytes were once decoded as a legacy Windows console encoding,
    # this repairs the text before we start removing "garbage" symbols.
    for source_encoding in ("cp866", "cp1251", "latin1"):
        try:
            candidate = text.encode(source_encoding).decode("utf-8")
        except (UnicodeEncodeError, UnicodeDecodeError):
            continue

        candidate_score = text_quality_score(candidate)
        if candidate_score > best_score:
            best_text = candidate
            best_score = candidate_score

    return best_text


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

        # Replace decorative or broken symbols with spaces so words do not glue
        # together after cleanup.
        cleaned.append(" ")

    return "".join(cleaned)


def normalize_wrapped_text(text: str) -> str:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    collapsed = re.sub(r"\s+", " ", " ".join(lines)).strip()
    collapsed = re.sub(r"\s+([,.;:!?])", r"\1", collapsed)
    collapsed = re.sub(r"(?:\.\s*){2,}", ". ", collapsed)
    collapsed = re.sub(r"\.\s+(?=[a-zа-яё])", " ", collapsed, flags=re.IGNORECASE)
    return re.sub(r"\s+", " ", collapsed).strip()


def mark_dialogue_boundaries(text: str) -> str:
    # Subtitle lines often glue several speaker turns together as
    # `Sentence? - Answer.`; we split only after a clear sentence ending.
    return re.sub(
        r'([.!?…]+["\'”’)]*)\s*-\s+(?=["\'«A-ZА-ЯЁ0-9])',
        r"\1\n",
        text,
    )


def split_line_into_sentences(line: str) -> list[str]:
    normalized = normalize_wrapped_text(line)
    if not normalized:
        return []

    normalized = mark_dialogue_boundaries(normalized)
    pattern = r".+?(?:[.!?…]+[\"'”’)]*|$)(?=\s+(?:[\"'“‘(]*[A-ZА-ЯЁ0-9])|$)"
    sentences: list[str] = []
    for chunk in normalized.splitlines():
        sentences.extend(
            match.group(0).strip() for match in re.finditer(pattern, chunk) if match.group(0).strip()
        )

    cleaned: list[str] = []
    for sentence in sentences:
        sentence = re.sub(r"\s+", " ", sentence).strip()
        sentence = re.sub(r"\s+([,.;:!?])", r"\1", sentence)
        sentence = re.sub(r"(?:\.\s*){2,}", ".", sentence)
        if sentence and not re.fullmatch(r"[.!?…]+", sentence):
            cleaned.append(sentence)

    return cleaned


def split_sentences(text: str) -> list[str]:
    sentences: list[str] = []

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        line_sentences = split_line_into_sentences(line)
        if line_sentences:
            sentences.extend(line_sentences)

    return sentences


def count_long_words(text: str, min_letters: int) -> int:
    return sum(1 for word in WORD_RE.findall(text) if len(word) > min_letters)


def filter_sentences(
    sentences: list[str], min_long_words: int, min_letters: int
) -> list[str]:
    return [
        sentence
        for sentence in sentences
        if count_long_words(sentence, min_letters=min_letters) >= min_long_words
    ]


def clean_text(text: str, min_long_words: int, min_letters: int) -> str:
    if not text.strip():
        raise ValueError("Input text is empty")

    text = unicodedata.normalize("NFC", repair_mojibake(text))
    text = strip_non_text_symbols(text)

    if looks_like_subtitle(text):
        text = strip_subtitle_metadata(text)

    sentences = split_sentences(text)
    if not sentences:
        raise ValueError("No sentences found in input text")

    filtered = filter_sentences(
        sentences,
        min_long_words=min_long_words,
        min_letters=min_letters,
    )
    if not filtered:
        raise ValueError("No sentences left after filtering")

    return "\n".join(filtered)


def clean_file(path: Path, min_long_words: int, min_letters: int) -> bool:
    original = path.read_text(encoding="utf-8")
    cleaned = clean_text(
        original,
        min_long_words=min_long_words,
        min_letters=min_letters,
    ) + "\n"

    if original == cleaned:
        return False

    path.write_text(cleaned, encoding="utf-8")
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
            "Remove sentences with too few long words and rewrite the file "
            "with one sentence per line."
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
    parser.add_argument(
        "--min-long-words",
        type=int,
        default=5,
        help="Keep only sentences with at least this many words longer than --min-letters.",
    )
    parser.add_argument(
        "--min-letters",
        type=int,
        default=3,
        help="Count only words whose length is greater than this threshold.",
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
            if clean_file(
                path,
                min_long_words=args.min_long_words,
                min_letters=args.min_letters,
            ):
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
