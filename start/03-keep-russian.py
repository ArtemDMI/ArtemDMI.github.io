#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Оставляет только русские блоки в .txt файлах sources/.

Использование:
  python start/03-keep-russian.py [--dry-run] [sources_dir]

Правила:
  - блок русский, если кириллицы > 50% от (кириллица + латиница);
  - английские блоки, прочерки и пустые строки удаляются;
  - предложение > 3 слов — с новой строки; короткие склеиваются в одну;
  - файл без русских блоков удаляется.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

CYRILLIC_RE = re.compile(r'[а-яА-ЯёЁ]')
LATIN_RE = re.compile(r'[a-zA-Z]')
SENTENCE_ENDS = '.!?…'


def cyrillic_ratio(text: str) -> float:
    cyr = len(CYRILLIC_RE.findall(text))
    lat = len(LATIN_RE.findall(text))
    total = cyr + lat
    if total == 0:
        return 0.0
    return cyr / total


def is_russian_block(text: str) -> bool:
    return cyrillic_ratio(text) > 0.5


def split_blocks(text: str) -> list[str]:
    blocks: list[str] = []
    current: list[str] = []

    for line in text.splitlines():
        stripped = line.strip()
        if stripped == '-' or not stripped:
            if current:
                blocks.append(' '.join(current))
                current = []
            continue
        current.append(stripped)

    if current:
        blocks.append(' '.join(current))
    return blocks


def split_sentences(text: str) -> list[str]:
    sentences: list[str] = []
    start = 0
    pos = 0
    length = len(text)

    while pos < length:
        if text[pos] in SENTENCE_ENDS:
            next_pos = pos + 1
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


def format_russian_text(text: str) -> str:
    lines: list[str] = []
    short_parts: list[str] = []

    for sentence in split_sentences(text):
        if len(sentence.split()) > 3:
            if short_parts:
                lines.append(' '.join(short_parts))
                short_parts = []
            lines.append(sentence)
        else:
            short_parts.append(sentence)

    if short_parts:
        lines.append(' '.join(short_parts))

    return '\n'.join(lines)


def process_file(path: Path, dry_run: bool) -> str:
    """Возвращает: kept | deleted | empty."""
    original = path.read_text(encoding='utf-8')
    russian_blocks = [b for b in split_blocks(original) if is_russian_block(b)]

    if not russian_blocks:
        if not dry_run:
            path.unlink()
        return 'deleted'

    result = '\n'.join(format_russian_text(block) for block in russian_blocks)
    if result and not result.endswith('\n'):
        result += '\n'

    if not dry_run:
        path.write_text(result, encoding='utf-8')
    return 'kept'


def main() -> None:
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    if hasattr(sys.stderr, 'reconfigure'):
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')

    parser = argparse.ArgumentParser(description='Оставить только русский текст в sources/')
    parser.add_argument(
        'sources_dir',
        nargs='?',
        default='sources',
        help='Каталог с .txt (по умолчанию: sources)',
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Только отчёт, без записи и удаления',
    )
    args = parser.parse_args()

    script_dir = Path(__file__).resolve().parent
    sources_dir = Path(args.sources_dir)
    if not sources_dir.is_absolute():
        sources_dir = (script_dir.parent / sources_dir).resolve()

    if not sources_dir.is_dir():
        print(f'Ошибка: каталог не найден: {sources_dir}', file=sys.stderr)
        sys.exit(1)

    txt_files = sorted(sources_dir.rglob('*.txt'))
    kept = deleted = 0

    for path in txt_files:
        status = process_file(path, args.dry_run)
        if status == 'kept':
            kept += 1
        else:
            deleted += 1
            print(f'Удалён: {path.relative_to(sources_dir.parent)}')

    mode = ' (dry-run)' if args.dry_run else ''
    print(f'Готово{mode}: обработано {len(txt_files)}, оставлено {kept}, удалено {deleted}')


if __name__ == '__main__':
    main()
