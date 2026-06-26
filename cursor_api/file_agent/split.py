"""Разбиение нормализованного текста на части и поиск суффиксных файлов для merge."""

from __future__ import annotations

import re
import sys
from pathlib import Path

MAX_LINES_PER_PART = 300
MAX_CHARS_PER_PART = 10000
MAX_CHARS_PER_NO_PUNCT_PART = 12000
SENTENCE_PUNCTUATION_RE = re.compile(r"[.!?…]")


def _has_sentence_punctuation(text: str) -> bool:
    return bool(SENTENCE_PUNCTUATION_RE.search(text))


def _split_long_token(token: str, max_chars: int) -> list[str]:
    return [token[index : index + max_chars] for index in range(0, len(token), max_chars)]


def _split_by_char_budget(text: str, max_chars: int) -> list[str]:
    collapsed = re.sub(r"\s+", " ", text).strip()
    if not collapsed:
        return []
    if len(collapsed) <= max_chars:
        return [collapsed]

    parts: list[str] = []
    current = ""

    def flush() -> None:
        nonlocal current
        if current:
            parts.append(current)
            current = ""

    for token in collapsed.split(" "):
        if not token:
            continue
        if len(token) > max_chars:
            flush()
            parts.extend(_split_long_token(token, max_chars))
            continue

        candidate = token if not current else f"{current} {token}"
        if len(candidate) > max_chars:
            flush()
            current = token
        else:
            current = candidate

    flush()
    return parts


def _should_use_char_budget(text: str, sentences: list[str]) -> bool:
    if not _has_sentence_punctuation(text):
        return True

    if not sentences:
        return False

    max_sentence_chars = max(len(sentence) for sentence in sentences)
    return len(sentences) <= 3 and max_sentence_chars > MAX_CHARS_PER_NO_PUNCT_PART


def split_normalized(text: str) -> list[str]:
    """Делит нормализованный текст (одно предложение на строку) на части по границам предложений."""
    sentences = [line for line in text.splitlines() if line.strip()]
    if not sentences:
        stripped = text.strip()
        return [stripped] if stripped else []

    if _should_use_char_budget(text, sentences):
        # Without sentence-ending punctuation, line count is arbitrary after normalization,
        # or the sentence split can collapse into a few giant lines, so we size parts
        # by character budget instead of trusting synthetic sentence lines.
        return _split_by_char_budget(" ".join(sentences), MAX_CHARS_PER_NO_PUNCT_PART)

    parts: list[str] = []
    current: list[str] = []
    current_lines = 0
    current_chars = 0

    def flush() -> None:
        nonlocal current, current_lines, current_chars
        if current:
            parts.append("\n".join(current))
            current = []
            current_lines = 0
            current_chars = 0

    for sentence in sentences:
        sentence_chars = len(sentence)
        if sentence_chars > MAX_CHARS_PER_PART:
            flush()
            print(
                f"[WARN] Single sentence exceeds {MAX_CHARS_PER_PART} chars "
                f"({sentence_chars}); kept intact in its own part.",
                file=sys.stderr,
            )
            parts.append(sentence)
            continue

        added_chars = sentence_chars if not current else sentence_chars + 1
        exceeds_lines = current and current_lines + 1 > MAX_LINES_PER_PART
        exceeds_chars = current and current_chars + added_chars > MAX_CHARS_PER_PART

        if exceeds_lines or exceeds_chars:
            flush()
            current = [sentence]
            current_lines = 1
            current_chars = sentence_chars
        else:
            current.append(sentence)
            current_lines += 1
            current_chars += added_chars

    flush()
    return parts


def part_paths(source: Path, extra_count: int) -> list[Path]:
    """Пути всех частей: source, sourceS001.ext, sourceS002.ext, …"""
    source = Path(source)
    if extra_count < 0:
        raise ValueError(f"extra_count must be >= 0, got {extra_count}")

    paths = [source]
    for index in range(1, extra_count + 1):
        paths.append(source.parent / f"{source.stem}S{index:03d}{source.suffix}")
    return paths


def _iter_existing_suffix_paths(source: Path) -> list[tuple[int, Path]]:
    stem = source.stem
    suffix = source.suffix
    pattern = re.compile(rf"^{re.escape(stem)}S(\d{{3}}){re.escape(suffix)}$")
    found: list[tuple[int, Path]] = []
    for path in source.parent.iterdir():
        if not path.is_file():
            continue
        match = pattern.match(path.name)
        if match:
            found.append((int(match.group(1)), path))
    found.sort(key=lambda item: item[0])
    return found


def check_split_conflicts(source: Path, paths: list[Path]) -> None:
    """Ошибка, если на диске остались лишние суффиксные части от старого разбиения."""
    source = Path(source)
    expected_suffix_count = max(len(paths) - 1, 0)
    conflicts = [
        path
        for number, path in _iter_existing_suffix_paths(source)
        if number > expected_suffix_count
    ]
    if conflicts:
        listed = ", ".join(str(path) for path in conflicts)
        raise ValueError(f"Split conflicts with existing part files: {listed}")


def write_parts(source: Path, parts: list[str]) -> list[Path]:
    """Пишет части на диск: первая в source, остальные в S00N рядом."""
    if not parts:
        raise ValueError("Cannot write split: no parts produced")

    source = Path(source)
    paths = part_paths(source, len(parts) - 1)
    if len(paths) != len(parts):
        raise ValueError("Part count does not match generated paths")

    check_split_conflicts(source, paths)
    for path, content in zip(paths, parts):
        path.write_text(content, encoding="utf-8", newline="\n")
    return paths


def find_existing_parts(source: Path) -> list[Path]:
    """Исходный файл и подряд идущие суффиксные части S001, S002, …"""
    source = Path(source)
    if not source.is_file():
        raise FileNotFoundError(f"Source file not found: {source}")

    parts = [source]
    index = 1
    while True:
        part_path = source.parent / f"{source.stem}S{index:03d}{source.suffix}"
        if part_path.is_file():
            parts.append(part_path)
            index += 1
        else:
            break
    return parts
