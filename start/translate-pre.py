#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт разбиения больших текстовых файлов на части по границам предложений.

ТРЕБОВАНИЯ: Windows System UTF-8 (intl.cpl > Administrative > Change system locale > Beta: Use Unicode UTF-8).

Использование:
  python translate-pre.py <абсолютный_путь_к_файлу>

Что делает:
  Если файл больше 7000 символов — делит на части по границам предложений:
  - Часть 1 остаётся в оригинальном файле.
  - Части 2, 3... → имяS001.txt, имяS002.txt и т.д.
  Если файл 7000 символов или меньше — ничего не делает.
"""

import sys
import os

# ---------------------------------------------------------------------------
# Константы
# ---------------------------------------------------------------------------

MAX_PART_SIZE = 7000   # максимальный размер части (символов)

# Символы конца предложения
SENTENCE_ENDS = '.!?'


# ---------------------------------------------------------------------------
# Вспомогательные функции
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Точка входа
# ---------------------------------------------------------------------------

def main():
    if len(sys.argv) < 2:
        print("Usage: python translate-pre.py <absolute_path_to_file>")
        sys.exit(1)

    file_path = sys.argv[1]

    if not os.path.exists(file_path):
        print(f"Error: file '{file_path}' not found.")
        sys.exit(1)

    try:
        with open(file_path, 'r', encoding='utf-8-sig') as f:
            original_text = f.read()
    except Exception as e:
        print(f"Error reading file: {e}")
        sys.exit(1)

    if not original_text.strip():
        print("Error: file is empty.")
        sys.exit(1)

    char_count = len(original_text)

    if char_count <= MAX_PART_SIZE:
        print("complete")
        sys.exit(0)

    parts = split_into_parts(original_text, MAX_PART_SIZE)
    total_parts = len(parts)
    part_paths = get_part_paths(file_path, total_parts - 1)

    # Часть 1 — перезаписываем оригинальный файл
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(remove_empty_lines(parts[0]))
    except Exception as e:
        print(f"Error writing file '{file_path}': {e}")
        sys.exit(1)

    # Части 2, 3... — создаём новые файлы
    for part_text, part_path in zip(parts[1:], part_paths):
        try:
            with open(part_path, 'w', encoding='utf-8') as f:
                f.write(remove_empty_lines(part_text))
        except Exception as e:
            print(f"Error writing file '{part_path}': {e}")
            sys.exit(1)

    print("complete")


if __name__ == "__main__":
    main()
