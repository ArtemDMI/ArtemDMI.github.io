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
SENTENCE_END_RE = re.compile(r'[.!?…]+["\'”’»)]*$')
SENTENCE_PUNCTUATION_RE = re.compile(r'[.!?…]+')
LEADING_CLOSERS_RE = re.compile(r'^[»”’"\')\]\}]+')
REDDIT_AVATAR_RE = re.compile(r"^\s*Аватар u/[A-Za-z0-9_-]+\s*$")
REDDIT_TIMESTAMP_RE = re.compile(r"^\s*\d+\s*(?:дн\.|ч\.|мин\.|сек\.)\s+назад\s*$")
REDDIT_COLLAPSED_REPLIES_RE = re.compile(r"^\s*Еще\s+\d+\s+ответ(?:ов|а)?\s*$")
REDDIT_USERNAME_RE = re.compile(r"^\s*[A-Za-z0-9_][A-Za-z0-9_-]{1,31}\s*$")
REDDIT_BADGE_LINE_RE = re.compile(
    r"^\s*(?:Значок профиля за достижение|Комментатор из топ-\d+%)"
    r"(?:\s+(?:Значок профиля за достижение|Комментатор из топ-\d+%))*\s*$"
)
SPACED_ELLIPSIS_RE = re.compile(r"(?:\.\s*){3,}")
REDDIT_UI_LINES = {
    "Нравится",
    "Не нравится",
    "Ответить",
    "Награда",
    "Поделиться",
    "Перейти к комментариям",
    "Вступить в беседу",
    "Сортировка по:",
    "Лучшие",
    "Найти комментарии",
    "Развернуть поиск по комментариям",
}
# Base personal pronouns are short by nature, so we keep only their dictionary
# forms significant to avoid dropping normal dialogue lines. Indirect and
# possessive forms stay excluded because they inflate fragment-heavy subtitles.
SIGNIFICANT_SHORT_WORDS = {
    "я",
    "ты",
    "он",
    "она",
    "оно",
    "мы",
    "вы",
    "они",
    "i",
    "you",
    "he",
    "she",
    "it",
    "we",
    "they",
}
DEFAULT_MIN_WORDS = 3
MIN_SIGNIFICANT_WORD_LENGTH = 4


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


def is_reddit_comment_header(lines: list[str], index: int) -> int:
    line = lines[index].strip()
    if not line:
        return 0

    if REDDIT_AVATAR_RE.fullmatch(line):
        consumed = 1

        next_index = index + consumed
        if next_index < len(lines) and REDDIT_USERNAME_RE.fullmatch(lines[next_index].strip()):
            consumed += 1
            next_index = index + consumed

        if next_index < len(lines) and lines[next_index].strip() == "•":
            consumed += 1
            next_index = index + consumed

        if next_index < len(lines) and REDDIT_TIMESTAMP_RE.fullmatch(lines[next_index].strip()):
            consumed += 1

        return consumed

    if not REDDIT_USERNAME_RE.fullmatch(line):
        return 0
    if index + 2 >= len(lines):
        return 0
    if lines[index + 1].strip() != "•":
        return 0
    if not REDDIT_TIMESTAMP_RE.fullmatch(lines[index + 2].strip()):
        return 0

    return 3


def strip_reddit_metadata(text: str) -> str:
    cleaned: list[str] = []
    lines = text.splitlines()
    index = 0
    skip_vote_count = False

    while index < len(lines):
        line = lines[index].strip()

        if not line:
            index += 1
            continue

        header_length = is_reddit_comment_header(lines, index)
        if header_length:
            index += header_length
            skip_vote_count = False
            continue

        if (
            line in REDDIT_UI_LINES
            or line == "•"
            or REDDIT_COLLAPSED_REPLIES_RE.fullmatch(line)
            or REDDIT_BADGE_LINE_RE.fullmatch(line)
        ):
            skip_vote_count = line in {"Нравится", "Не нравится"}
            index += 1
            continue

        if skip_vote_count and re.fullmatch(r"\d+", line):
            index += 1
            continue

        skip_vote_count = False
        cleaned.append(line)
        index += 1

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


def normalize_line_text(text: str) -> str:
    # Reddit exports often space out ellipses as `. . .`, which can keep
    # throwaway fragments alive; collapsing them to one stop lets short junk drop.
    text = SPACED_ELLIPSIS_RE.sub(". ", text)
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"\s+([,.;:!?])", r"\1", text)
    text = re.sub(r"([,.;:!?])(?=[^\s\"'”’)\]\}])", r"\1 ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def mark_dialogue_boundaries(text: str) -> str:
    # Subtitle lines often glue several speaker turns together as
    # `Sentence? - Answer.`; we split only after a clear sentence ending.
    return re.sub(
        r'([.!?…]+["\'”’»)]*)\s*-\s+(?=["\'«A-ZА-ЯЁ0-9])',
        r"\1\n",
        text,
    )


def split_chunk_by_punctuation(chunk: str) -> list[str]:
    # Any sentence-ending punctuation is treated as a hard boundary because
    # noisy subtitle exports often start the next sentence with junk or lowercase.
    pattern = r".+?(?:[.!?…]+[\"'”’»)]*|$)"
    matches = [match.group(0).strip() for match in re.finditer(pattern, chunk)]
    return [match for match in matches if match]


def rebalance_leading_closers(sentences: list[str]) -> list[str]:
    rebalanced: list[str] = []

    for sentence in sentences:
        current = sentence.strip()
        if not current:
            continue

        if rebalanced:
            match = LEADING_CLOSERS_RE.match(current)
            if match:
                closers = match.group(0)
                rebalanced[-1] = rebalanced[-1].rstrip() + closers
                current = current[match.end() :].lstrip()
                current = normalize_line_text(current)
                if not current:
                    continue

        rebalanced.append(current)

    return rebalanced


def split_line_into_sentences(line: str) -> list[str]:
    normalized = normalize_line_text(line)
    if not normalized:
        return []

    normalized = mark_dialogue_boundaries(normalized)
    sentences: list[str] = []

    for chunk in normalized.splitlines():
        chunk = normalize_line_text(re.sub(r"^\s*-\s*", "", chunk))
        if not chunk:
            continue

        if SENTENCE_PUNCTUATION_RE.search(chunk):
            sentences.extend(split_chunk_by_punctuation(chunk))
            continue

        # When punctuation is missing entirely, the source line is the safest
        # boundary we have, so we keep it as a single candidate sentence.
        sentences.append(chunk)

    cleaned: list[str] = []
    for sentence in sentences:
        sentence = normalize_line_text(sentence)
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

    return rebalance_leading_closers(sentences)


def significant_word_count(text: str) -> int:
    count = 0
    for word in WORD_RE.findall(text):
        lowered = word.casefold()
        if lowered in SIGNIFICANT_SHORT_WORDS or len(lowered) >= MIN_SIGNIFICANT_WORD_LENGTH:
            count += 1
    return count


def filter_sentences(sentences: list[str], min_words: int) -> list[str]:
    return [
        sentence
        for sentence in sentences
        if significant_word_count(sentence) >= min_words
    ]


def filter_normalized_text(text: str, min_words: int = DEFAULT_MIN_WORDS) -> str:
    if not text.strip():
        raise ValueError("Input text is empty")

    sentences = split_sentences(text)
    if not sentences:
        raise ValueError("No sentences found in input text")

    filtered = filter_sentences(sentences, min_words=min_words)
    if not filtered:
        raise ValueError("No sentences left after filtering")

    return "\n".join(filtered)


def clean_text(text: str, min_words: int) -> str:
    if not text.strip():
        raise ValueError("Input text is empty")

    text = unicodedata.normalize("NFC", repair_mojibake(text))
    text = strip_non_text_symbols(text)
    text = strip_reddit_metadata(text)

    if looks_like_subtitle(text):
        text = strip_subtitle_metadata(text)

    # Raw cleanup and file_agent normalization must share one filter entrypoint
    # so further edits in start/ automatically affect both flows.
    return filter_normalized_text(text, min_words=min_words)


def clean_file(path: Path, min_words: int) -> bool:
    original = path.read_text(encoding="utf-8")
    cleaned = clean_text(original, min_words=min_words) + "\n"

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
            "Remove sentences with too few significant words and rewrite the "
            "file with one sentence per line."
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
        "--min-words",
        type=int,
        default=DEFAULT_MIN_WORDS,
        help=(
            "Keep only sentences with at least this many significant words. "
            "A significant word is longer than 3 letters, except for: я, ты, вы, мы."
        ),
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
                min_words=args.min_words,
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
