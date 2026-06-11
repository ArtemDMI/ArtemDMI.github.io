#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Очистка текстовых файлов: пробелы и нормализация абзацев.

Использование:
  python 00-clean.py --clean <файл1> [файл2 ...]

Пример:
  python start/00-clean.py --clean sources/13/botswana_success_story.txt sources/13/bounty_hunter_wasteland_2.txt

Что делает:
  - убирает двойные (и более) пробелы до одного;
  - склеивает разорванные строки в сплошной текст;
  - если есть пунктуация (. ! ? …) — группирует предложения в абзацы
    (~4 предложения или ~320 символов);
  - если пунктуации нет — группирует по ~50 слов на абзац.

Заголовок (Title:, URL:) в начале файла сохраняется.
"""

import argparse
import re
import sys
from pathlib import Path

SENTENCE_ENDS = '.!?…'
SENTENCES_PER_PARA = 4
WORDS_PER_PARA = 50
TARGET_CHARS = 320


def normalize_spaces(text: str) -> str:
    return re.sub(r' +', ' ', text).strip()


def split_sentences(text: str) -> list[str]:
    sentences: list[str] = []
    start = 0
    pos = 0
    length = len(text)

    while pos < length:
        if text[pos] in SENTENCE_ENDS:
            next_pos = pos + 1
            if next_pos >= length or text[next_pos] == ' ':
                sent = text[start:next_pos].strip()
                if sent:
                    sentences.append(sent)
                start = next_pos
                while start < length and text[start] == ' ':
                    start += 1
                pos = start
                continue
        pos += 1

    tail = text[start:].strip()
    if tail:
        sentences.append(tail)
    return sentences


def has_sentence_punctuation(text: str) -> bool:
    return any(ch in text for ch in SENTENCE_ENDS)


def form_paragraphs(text: str) -> list[str]:
    text = normalize_spaces(text)
    if not text:
        return []

    if has_sentence_punctuation(text):
        sentences = split_sentences(text)
        paragraphs: list[str] = []
        current: list[str] = []
        current_len = 0

        for sent in sentences:
            current.append(sent)
            current_len += len(sent)
            if len(current) >= SENTENCES_PER_PARA or current_len >= TARGET_CHARS:
                paragraphs.append(' '.join(current))
                current = []
                current_len = 0

        if current:
            paragraphs.append(' '.join(current))
        return paragraphs

    words = text.split()
    return [
        ' '.join(words[i:i + WORDS_PER_PARA])
        for i in range(0, len(words), WORDS_PER_PARA)
    ]


def split_header_body(lines: list[str]) -> tuple[list[str], list[str]]:
    """Сохраняет блок Title:/URL: в начале файла."""
    header: list[str] = []
    i = 0

    while i < len(lines):
        stripped = lines[i].strip()
        if not stripped:
            header.append(lines[i])
            i += 1
            continue
        if stripped.startswith(('Title:', 'URL:', 'title:', 'url:')):
            header.append(lines[i])
            i += 1
            continue
        break

    while header and not header[-1].strip():
        header.pop()

    return header, lines[i:]


def clean_text(text: str) -> str:
    lines = text.splitlines()
    header, body_lines = split_header_body(lines)

    body_parts = [
        normalize_spaces(line)
        for line in body_lines
        if line.strip()
    ]
    paragraphs = form_paragraphs(' '.join(body_parts))

    result: list[str] = []
    if header:
        result.extend(header)
        result.append('')
    result.extend(paragraphs)
    return '\n'.join(result) + '\n'


def resolve_path(path_str: str, script_dir: Path) -> Path:
    path = Path(path_str)
    if path.is_file():
        return path.resolve()

    repo_root = script_dir.parent
    candidate = repo_root / path
    if candidate.is_file():
        return candidate.resolve()

    return path.resolve()


def main() -> None:
    parser = argparse.ArgumentParser(description='Очистка текстовых файлов')
    parser.add_argument(
        '--clean',
        nargs='+',
        metavar='FILE',
        help='Файлы для очистки',
    )
    args = parser.parse_args()

    if not args.clean:
        parser.print_help()
        sys.exit(1)

    script_dir = Path(__file__).resolve().parent
    errors = 0

    for file_arg in args.clean:
        path = resolve_path(file_arg, script_dir)
        if not path.is_file():
            print(f'Ошибка: файл не найден: {file_arg}', file=sys.stderr)
            errors += 1
            continue

        original = path.read_text(encoding='utf-8')
        cleaned = clean_text(original)
        path.write_text(cleaned, encoding='utf-8')
        print(f'Очищен: {path}')

    if errors:
        sys.exit(1)


if __name__ == '__main__':
    main()
