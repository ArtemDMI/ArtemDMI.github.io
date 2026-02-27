#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт разбивки текста на блоки ~300 символов для перевода.

ТРЕБОВАНИЯ: Windows System UTF-8 (intl.cpl > Administrative > Change system locale > Beta: Use Unicode UTF-8).

Использование:
  python translate-post.py <абсолютный_путь_к_файлу>

Что делает:
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


# ---------------------------------------------------------------------------
# Константы
# ---------------------------------------------------------------------------

BLOCK_SIZE = 300       # минимальное количество символов в блоке

# Символы конца предложения
SENTENCE_ENDS = '.!?'


# ---------------------------------------------------------------------------
# Вспомогательные функции
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Точка входа
# ---------------------------------------------------------------------------

def main():
    if len(sys.argv) < 2:
        print("Usage: python translate-post.py <absolute_path_to_file>")
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

    if is_already_processed(original_text):
        print("complete")
        sys.exit(0)

    result = build_blocks(original_text)

    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(result)
    except Exception as e:
        print(f"Error writing file: {e}")
        sys.exit(1)

    print("complete")


if __name__ == "__main__":
    main()
