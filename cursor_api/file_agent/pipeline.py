"""Оркестрация режимов translate (-t) и merge (-merge)."""

from __future__ import annotations

import concurrent.futures
import re
import sys
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from file_agent import normalization, runner, split, validation

MAX_ATTEMPTS = 3
PART_TIMEOUT = 90.0
REQUEST_PAUSE_SECONDS = 2.2
MERGE_JOIN = "\n\n"
PROMPT_FILE = Path(__file__).resolve().parent / "prompt.md"

# Точка подмены в тестах без реального API.
run_part_fn: Callable[..., None] = runner.run_part


@dataclass(frozen=True, slots=True)
class PartContext:
    original_text: str
    source_size: int


@dataclass(frozen=True, slots=True)
class PartOutcome:
    path: Path
    ok: bool
    reason: str = ""


class RequestPacer:
    def __init__(self, interval_seconds: float) -> None:
        self._interval_seconds = interval_seconds
        self._lock = threading.Lock()
        self._next_start = 0.0

    def wait(self) -> None:
        with self._lock:
            now = time.monotonic()
            start_at = max(now, self._next_start)
            self._next_start = start_at + self._interval_seconds

        delay = start_at - now
        if delay > 0:
            # Cursor SDK has a per-minute request limit; spacing starts prevents bursts.
            time.sleep(delay)


def _load_base_prompt() -> str:
    if not PROMPT_FILE.is_file():
        raise FileNotFoundError(f"Prompt file not found: {PROMPT_FILE}")
    text = PROMPT_FILE.read_text(encoding="utf-8")
    if not text.strip():
        raise ValueError(f"Prompt file is empty: {PROMPT_FILE}")
    return text


def _build_system_prompt(story_context: str) -> str:
    context = story_context.strip()
    if not context:
        raise ValueError("Story context must not be empty")
    if not context.isascii():
        raise ValueError("Story context must be written in English ASCII")

    return (
        "# Story Context\n\n"
        "Use this context for every part before translating. It is authoritative "
        "for character names, genders, relationships, narrator point of view, and "
        "consistent pronouns. Do not translate this context as output.\n\n"
        f"{context}\n\n"
        "# Translation Instructions\n\n"
        f"{_load_base_prompt()}"
    )


def _prepare_parts(source: Path) -> tuple[list[Path], dict[Path, PartContext]]:
    if not source.is_file():
        raise FileNotFoundError(f"Source file not found: {source}")

    raw_text = source.read_text(encoding="utf-8")
    normalized = normalization.normalize_text(raw_text)
    part_texts = split.split_normalized(normalized)
    if not part_texts:
        raise ValueError("Split produced no parts")

    paths = split.part_paths(source, len(part_texts) - 1)
    contexts: dict[Path, PartContext] = {}
    for path, text in zip(paths, part_texts):
        contexts[path] = PartContext(
            original_text=text,
            source_size=validation.count_non_whitespace(text),
        )

    split.write_parts(source, part_texts)
    return paths, contexts


def _process_part(
    part_path: Path,
    context: PartContext,
    system_prompt: str,
    pacer: RequestPacer,
) -> PartOutcome:
    last_reason = "unknown error"
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            pacer.wait()
            run_part_fn(part_path, system_prompt=system_prompt, timeout=PART_TIMEOUT)
        except Exception as err:
            last_reason = f"attempt {attempt}: {err}"
            continue

        try:
            translated = part_path.read_text(encoding="utf-8")
            translated = _remove_blank_lines(translated)
            part_path.write_text(translated, encoding="utf-8", newline="\n")
            result = validation.validate_translation(
                context.original_text,
                translated,
                file=part_path,
            )
        except Exception as err:
            last_reason = f"attempt {attempt}: {err}"
            continue

        if result.ok:
            return PartOutcome(part_path, True)

        last_reason = (
            f"attempt {attempt}: validation {result.status} "
            f"(ratio {result.ratio:.2f})"
        )

    return PartOutcome(part_path, False, last_reason)


def _remove_blank_lines(text: str) -> str:
    return "\n".join(line for line in text.splitlines() if line.strip())


def _normalize_merged_translation(texts: list[str]) -> str:
    # Merge output is normalized again so edited parts still produce a consistent
    # "one sentence per line, or up to four very short ones" final file.
    merged = normalization.normalize_wrapped_text(MERGE_JOIN.join(texts))
    if not merged:
        raise ValueError("Merged text is empty")

    if not re.search(r"[.!?…]", merged):
        return "\n".join(normalization.merge_short_sentences([merged]))

    raw_sentences = re.findall(r'[^.!?…]+(?:[.!?…]+["\'”’)]*|$)', merged)
    sentences = normalization.clean_sentences(raw_sentences)
    if not sentences:
        raise ValueError("No sentences found in merged text")
    return "\n".join(normalization.merge_short_sentences(sentences))


def _print_summary(outcomes: list[PartOutcome]) -> None:
    total = len(outcomes)
    ok_count = sum(1 for item in outcomes if item.ok)
    failed = [item for item in outcomes if not item.ok]

    print("Сводка перевода:")
    print(f"  Всего частей: {total}")
    print(f"  Успешно: {ok_count}")
    print(f"  Ошибки: {len(failed)}")
    if failed:
        print("  Проблемные файлы:")
        for item in failed:
            print(f"    - {item.path}: {item.reason}")


def run_translate(source: Path, story_context: str) -> int:
    source = Path(source).expanduser().resolve()
    try:
        system_prompt = _build_system_prompt(story_context)
        part_paths, contexts = _prepare_parts(source)
    except (FileNotFoundError, ValueError, OSError) as err:
        print(f"Ошибка: {err}", file=sys.stderr)
        return 1

    outcomes: list[PartOutcome] = []
    pacer = RequestPacer(REQUEST_PAUSE_SECONDS)
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(part_paths)) as pool:
        futures = {
            pool.submit(_process_part, path, contexts[path], system_prompt, pacer): path
            for path in part_paths
        }
        for future in concurrent.futures.as_completed(futures):
            outcomes.append(future.result())

    outcomes.sort(key=lambda item: part_paths.index(item.path))
    _print_summary(outcomes)
    return 0 if all(item.ok for item in outcomes) else 1


def _orphan_suffix_parts(source: Path, consecutive_suffix_count: int) -> list[Path]:
    """Суффиксные части с номером выше подряд идущей цепочки — признак разрыва."""
    pattern = re.compile(
        rf"^{re.escape(source.stem)}S(\d{{3}}){re.escape(source.suffix)}$"
    )
    orphans: list[Path] = []
    for path in source.parent.iterdir():
        if not path.is_file():
            continue
        match = pattern.match(path.name)
        if match and int(match.group(1)) > consecutive_suffix_count:
            orphans.append(path)
    orphans.sort(key=lambda item: item.name.lower())
    return orphans


def _print_merge_summary(part_count: int, target: Path, deleted: list[Path]) -> None:
    print("Сводка сборки:")
    print(f"  Собрано файлов: {part_count}")
    print(f"  Результат записан в: {target}")
    if deleted:
        print(f"  Удалено суффиксных частей: {len(deleted)}")
        for path in deleted:
            print(f"    - {path}")


def run_merge(source: Path) -> int:
    source = Path(source).expanduser().resolve()
    try:
        parts = split.find_existing_parts(source)
        orphans = _orphan_suffix_parts(source, len(parts) - 1)
        if orphans:
            listed = ", ".join(str(path) for path in orphans)
            raise ValueError(f"Gap in part numbering: {listed}")

        texts = [path.read_text(encoding="utf-8") for path in parts]
        merged_text = _normalize_merged_translation(texts)
        source.write_text(merged_text, encoding="utf-8", newline="\n")

        suffix_parts = parts[1:]
        for path in suffix_parts:
            path.unlink()
    except (FileNotFoundError, ValueError, OSError) as err:
        print(f"Ошибка: {err}", file=sys.stderr)
        return 1

    _print_merge_summary(len(parts), source, suffix_parts)
    return 0
