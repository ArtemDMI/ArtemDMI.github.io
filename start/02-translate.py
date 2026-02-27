#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт разбивки текста на блоки ~300 символов для перевода.

ТРЕБОВАНИЯ: Windows System UTF-8 (intl.cpl > Administrative > Change system locale > Beta: Use Unicode UTF-8).

Использование:
  python translate-post.py
  python translate-post.py <абсолютный_путь_к_файлу>

Что делает:
  Массовый режим (без аргументов):
    обрабатывает все файлы внутри папки sources/ рекурсивно,
    кроме sources/.gitignore.

  Одиночный режим (с аргументом пути к файлу):
    обрабатывает только указанный файл.

  Скрипт ориентируется по своему собственному расположению (папка start/),
  текущая рабочая директория не важна.

  1. Проверяет, обработан ли файл уже (паттерн блоков). Если да — пропускает.
  2. Нарезает текст на блоки ~300 символов (до конца предложения).
  3. Каждый блок оформляется по схеме:
       -
       [Русский текст блока]
       -
       -
       -
       [пустая строка — место для английского перевода]
     Между блоками нет дополнительных разделителей — пустая строка является местом для перевода.

Пример вывода:
  complete
"""

import sys
import os
import re
from pathlib import Path


# ---------------------------------------------------------------------------
# Константы
# ---------------------------------------------------------------------------

BLOCK_SIZE = 300       # минимальное количество символов в блоке

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
    Проверяет, содержит ли текст паттерн обработанного блока.
    Паттерн: строка "-", затем любой текст, затем три строки "-".
    """
    pattern = re.compile(
        r'^-\n.+\n-\n-\n-$',
        re.MULTILINE
    )
    return bool(pattern.search(text))


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


def build_blocks(text: str, block_size: int = BLOCK_SIZE) -> str:
    """
    Нарезает текст на блоки ~block_size символов (до конца предложения).
    Возвращает готовый контент файла с блоками.

    Формат блока:
      -
      [текст]
      -
      -
      -
      [пустая строка — место для английского]
    """
    # Нормализуем текст: убираем лишние переносы, склеиваем в одну строку
    normalized = ' '.join(text.split())

    blocks = []
    start = 0
    length = len(normalized)

    while start < length:
        if start + block_size >= length:
            block_text = normalized[start:].strip()
            if block_text:
                blocks.append(block_text)
            break

        end = find_sentence_end(normalized, start + block_size)
        block_text = normalized[start:end].strip()
        if block_text:
            blocks.append(block_text)
        start = end

        while start < length and normalized[start] == ' ':
            start += 1

    lines = []
    for block_text in blocks:
        lines.append('-')
        lines.append(block_text)
        lines.append('-')
        lines.append('-')
        lines.append('-')
        lines.append('')   # пустая строка — место для английского перевода

    return '\n'.join(lines)


def iter_source_files(project_root: Path) -> list[Path]:
    sources_dir = project_root / "sources"
    if not sources_dir.exists():
        print(f"Error: sources dir not found: {sources_dir}")
        raise SystemExit(1)

    result: list[Path] = []
    for p in sources_dir.rglob("*"):
        if not p.is_file():
            continue
        # Исключение ровно одного файла: sources/.gitignore
        if p == (sources_dir / ".gitignore"):
            continue
        result.append(p)

    result.sort(key=lambda x: str(x).lower())
    return result


def process_file(file_path: Path) -> tuple[bool, str]:
    """
    Возвращает (ok, status):
      - ok=False означает, что произошла ошибка обработки файла
      - status: 'complete' | 'skipped' | 'processed' | 'error'
    """
    if not file_path.exists():
        print(f"Error: file '{file_path}' not found.")
        return False, "error"

    try:
        original_text = file_path.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError:
        print(f"Error reading file (encoding): {file_path}")
        return False, "error"
    except Exception as e:
        print(f"Error reading file '{file_path}': {e}")
        return False, "error"

    if not original_text.strip():
        print(f"Error: file is empty: {file_path}")
        return False, "error"

    if is_already_processed(original_text):
        return True, "skipped"

    result = build_blocks(original_text)

    try:
        file_path.write_text(result, encoding="utf-8")
    except Exception as e:
        print(f"Error writing file '{file_path}': {e}")
        return False, "error"

    return True, "processed"


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
        print("complete")
        return

    # Одиночный режим: совместимость со старым вызовом
    file_path = Path(sys.argv[1])
    ok, _status = process_file(file_path)
    if not ok:
        raise SystemExit(1)
    print("complete")


if __name__ == "__main__":
    main()
