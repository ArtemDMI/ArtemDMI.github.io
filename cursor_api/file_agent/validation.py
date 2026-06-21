"""Проверка длины перевода: символы без пробелов и допустимое отношение 60%..140%."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

MIN_RATIO = 0.60
MAX_RATIO = 1.40


def count_non_whitespace(text: str) -> int:
    """Считает символы строки, не являющиеся пробельными."""
    return sum(1 for char in text if not char.isspace())


@dataclass(frozen=True, slots=True)
class ValidationResult:
    file: Path | None
    source_size: int
    translated_size: int
    ratio: float
    status: str

    @property
    def ok(self) -> bool:
        return self.status == "ok"


def validate_translation(
    source: str,
    translated: str,
    *,
    file: Path | None = None,
) -> ValidationResult:
    """Сравнивает длину перевода с исходником; ratio = translated / source без пробелов."""
    source_size = count_non_whitespace(source)
    if source_size == 0:
        raise ValueError("Source text has zero non-whitespace characters")

    translated_size = count_non_whitespace(translated)
    ratio = translated_size / source_size

    if ratio < MIN_RATIO:
        status = "too_short"
    elif ratio > MAX_RATIO:
        status = "too_long"
    else:
        status = "ok"

    return ValidationResult(
        file=file,
        source_size=source_size,
        translated_size=translated_size,
        ratio=ratio,
        status=status,
    )
