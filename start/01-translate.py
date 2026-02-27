#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт разбиения больших текстовых файлов на части по границам предложений.

ТРЕБОВАНИЯ: Windows System UTF-8 (intl.cpl > Administrative > Change system locale > Beta: Use Unicode UTF-8).

Использование:
  python translate-pre.py
  python translate-pre.py <абсолютный_путь_к_файлу>

Что делает:
  Если файл больше 7000 символов — делит на части по границам предложений,
  но только если файл НЕ выглядит уже обработанным (размеченным блоками для перевода).

  Массовый режим (без аргументов):
    обрабатывает все файлы внутри папки sources/ рекурсивно,
    кроме sources/.gitignore.

  Одиночный режим (с аргументом пути к файлу):
    обрабатывает только указанный файл.

  Скрипт ориентируется по своему собственному расположению (папка start/),
  текущая рабочая директория не важна.

  Разбиение:
  - Часть 1 остаётся в оригинальном файле.
  - Части 2, 3... → имяS001.txt, имяS002.txt и т.д.
  Если файл 7000 символов или меньше — ничего не делает.
"""

import sys
import os
import re
from pathlib import Path

# ---------------------------------------------------------------------------
# Константы
# ---------------------------------------------------------------------------

MAX_PART_SIZE = 7000   # максимальный размер части (символов)

# Символы конца предложения
SENTENCE_ENDS = '.!?'


# ---------------------------------------------------------------------------
# Вспомогательные функции
# ---------------------------------------------------------------------------

def ensure_run_from_script_dir() -> Path:
    """
    Возвращает директорию, где лежит скрипт.
    Не требует, чтобы cwd совпадал с этой директорией.
    """
    script_dir = Path(__file__).resolve().parent
    return script_dir


def is_already_processed(text: str) -> bool:
    """
    Проверяет, содержит ли текст паттерн обработанного блока для перевода.

    1) Строгий паттерн из translate-post.py:
       строка "-", затем любой текст, затем три строки "-".
    2) Более мягкая эвристика:
       если в тексте есть как минимум две строки, которые равны "-" (с учётом пробелов).
    """
    strict = re.compile(r'^-\n.+\n-\n-\n-$', re.MULTILINE)
    if strict.search(text):
        return True

    dash_lines = 0
    for line in text.splitlines():
        if line.strip() == '-':
            dash_lines += 1
            if dash_lines >= 2:
                return True
    return False


def find_sentence_end(text: str, start: int) -> int:
    """
    Начиная с позиции start, ищет конец предложения (. ! ?) после которого
    идёт пробел, перенос строки или конец строки.
    Возвращает позицию ПОСЛЕ знака конца предложения (включая его).
    Если не найдено — возвращает len(text).
    """
    pos = start
    length = len(text)
    while pos < length:
        if text[pos] in SENTENCE_ENDS:
            next_pos = pos + 1
            if next_pos >= length or text[next_pos] in (' ', '\n', '\r', '\t'):
                return next_pos
        pos += 1
    return length


def split_into_parts(text: str, max_chars: int = MAX_PART_SIZE) -> list:
    """
    Делит текст на части не более max_chars символов каждая.
    Граница — конец предложения, ближайший к позиции max_chars.
    Возвращает список строк (частей).
    """
    parts = []
    start = 0
    length = len(text)

    while start < length:
        if start + max_chars >= length:
            parts.append(text[start:].strip())
            break

        end = find_sentence_end(text, start + max_chars)
        parts.append(text[start:end].strip())
        start = end

        while start < length and text[start] in (' ', '\n', '\r', '\t'):
            start += 1

    return [p for p in parts if p]


def remove_empty_lines(text: str) -> str:
    """
    Удаляет все пустые строки (и строки только из пробелов) из текста.
    """
    lines = text.splitlines()
    return '\n'.join(line for line in lines if line.strip())


def get_part_paths(file_path: str, count: int) -> list:
    """
    Генерирует пути для дополнительных частей файла.
    Пример: /path/omi_blabla.txt → ['/path/omi_blablaS001.txt', ...]
    count — количество дополнительных частей (не считая оригинала).
    """
    dir_name = os.path.dirname(file_path)
    base_name = os.path.basename(file_path)
    name, ext = os.path.splitext(base_name)

    paths = []
    for i in range(1, count + 1):
        part_name = f"{name}S{i:03d}{ext}"
        paths.append(os.path.join(dir_name, part_name))
    return paths


def iter_source_files(project_root: Path) -> list[Path]:
    sources_dir = project_root / "sources"
    if not sources_dir.exists():
        print(f"[ERROR] Error: sources dir not found: {sources_dir}")
        raise SystemExit(1)

    result: list[Path] = []
    for p in sources_dir.rglob("*"):
        if not p.is_file():
            continue
        # Исключение ровно одного файла: sources/.gitignore
        if p == (sources_dir / ".gitignore"):
            continue
        result.append(p)

    # стабильный порядок (чтобы массовая обработка была детерминированной)
    result.sort(key=lambda x: str(x).lower())
    return result


def process_file(file_path: Path) -> tuple[bool, str]:
    """
    Возвращает (ok, status):
      - ok=False означает, что произошла ошибка обработки файла
      - status: 'complete' | 'skipped' | 'split' | 'error'
    """
    if not file_path.exists():
        print(f"[ERROR] Error: file '{file_path}' not found.")
        return False, "error"

    try:
        original_text = file_path.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError:
        print(f"[ERROR] Error reading file (encoding): {file_path}")
        return False, "error"
    except Exception as e:
        print(f"[ERROR] Error reading file '{file_path}': {e}")
        return False, "error"

    if not original_text.strip():
        print(f"[ERROR] Error: file is empty: {file_path}")
        return False, "error"

    # Если файл уже размечен блоками перевода — не трогаем его, даже если он большой.
    if is_already_processed(original_text):
        return True, "skipped"

    if len(original_text) <= MAX_PART_SIZE:
        return True, "complete"

    parts = split_into_parts(original_text, MAX_PART_SIZE)
    if not parts:
        print(f"[ERROR] Error: split produced no parts: {file_path}")
        return False, "error"

    total_parts = len(parts)
    part_paths = get_part_paths(str(file_path), total_parts - 1)

    # Часть 1 — перезаписываем оригинальный файл
    try:
        file_path.write_text(remove_empty_lines(parts[0]), encoding="utf-8")
    except Exception as e:
        print(f"[ERROR] Error writing file '{file_path}': {e}")
        return False, "error"

    # Части 2, 3... — создаём новые файлы
    for part_text, part_path in zip(parts[1:], part_paths):
        try:
            Path(part_path).write_text(remove_empty_lines(part_text), encoding="utf-8")
        except Exception as e:
            print(f"[ERROR] Error writing file '{part_path}': {e}")
            return False, "error"

    return True, "split"


# ---------------------------------------------------------------------------
# Точка входа
# ---------------------------------------------------------------------------

def main():
    ensure_run_from_script_dir()

    script_dir = Path(__file__).resolve().parent
    project_root = script_dir.parent

    # Массовый режим: без аргументов обрабатываем sources/*
    if len(sys.argv) == 1:
        files = iter_source_files(project_root)
        had_errors = False
        for fp in files:
            ok, _status = process_file(fp)
            if not ok:
                had_errors = True
        if had_errors:
            raise SystemExit(1)
        print("[OK] complete")
        return

    # Одиночный режим: совместимость со старым вызовом
    file_path = Path(sys.argv[1])
    ok, _status = process_file(file_path)
    if not ok:
        raise SystemExit(1)
    print("[OK] complete")


if __name__ == "__main__":
    main()
