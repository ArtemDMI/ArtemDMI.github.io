#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Склеивает части nameS001.txt, nameS002.txt, ... в основной name.txt.

Использование:
  python start/04-merge-parts.py [--dry-run] [каталог ...]

По умолчанию обрабатывает все подкаталоги sources/.
"""

from __future__ import annotations

import argparse
import re
import sys
from collections import defaultdict
from pathlib import Path

PART_RE = re.compile(r'^(.+)S(\d+)\.txt$', re.IGNORECASE)


def read_part(path: Path) -> str:
    return path.read_text(encoding='utf-8').rstrip('\n')


def merge_group(main_path: Path, part_paths: list[Path]) -> str:
    chunks = [read_part(main_path), *(read_part(p) for p in part_paths)]
    chunks = [c for c in chunks if c]
    if not chunks:
        return ''
    return '\n'.join(chunks) + '\n'


def find_groups(directory: Path) -> list[tuple[Path, list[Path]]]:
    parts_by_base: dict[str, list[tuple[int, Path]]] = defaultdict(list)

    for path in directory.glob('*.txt'):
        match = PART_RE.match(path.name)
        if not match:
            continue
        base_name, number = match.group(1), int(match.group(2))
        parts_by_base[base_name].append((number, path))

    groups: list[tuple[Path, list[Path]]] = []
    for base_name, numbered_parts in sorted(parts_by_base.items()):
        main_path = directory / f'{base_name}.txt'
        if not main_path.is_file():
            print(f'Пропуск: нет основного файла для {base_name} ({directory})', file=sys.stderr)
            continue
        numbered_parts.sort(key=lambda item: item[0])
        groups.append((main_path, [path for _, path in numbered_parts]))

    return groups


def verify_merge(main_path: Path, part_paths: list[Path], merged: str) -> bool:
    expected = merge_group(main_path, part_paths)
    # Сверяем с исходниками до перезаписи основного файла.
    original_main = read_part(main_path)
    expected_from_sources = '\n'.join(
        chunk for chunk in [original_main, *(read_part(p) for p in part_paths)] if chunk
    )
    if expected_from_sources:
        expected_from_sources += '\n'
    return merged == expected_from_sources


def process_directory(directory: Path, dry_run: bool) -> tuple[int, int]:
    groups = find_groups(directory)
    merged_count = 0
    removed_count = 0

    for main_path, part_paths in groups:
        if not part_paths:
            continue

        merged = merge_group(main_path, part_paths)
        if not verify_merge(main_path, part_paths, merged):
            print(f'Ошибка проверки: {main_path}', file=sys.stderr)
            continue

        if dry_run:
            print(
                f'[dry-run] {main_path.name}: '
                f'1 + {len(part_paths)} частей -> {len(merged.splitlines())} строк'
            )
        else:
            main_path.write_text(merged, encoding='utf-8')
            for part_path in part_paths:
                part_path.unlink()
            print(f'Склеено: {main_path} (+{len(part_paths)} частей)')

        merged_count += 1
        removed_count += len(part_paths)

    return merged_count, removed_count


def main() -> None:
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    if hasattr(sys.stderr, 'reconfigure'):
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')

    parser = argparse.ArgumentParser(description='Склеить nameS00N.txt в name.txt')
    parser.add_argument(
        'directories',
        nargs='*',
        help='Каталоги для обработки (по умолчанию: все подкаталоги sources/)',
    )
    parser.add_argument('--dry-run', action='store_true', help='Без записи и удаления')
    args = parser.parse_args()

    script_dir = Path(__file__).resolve().parent
    repo_root = script_dir.parent

    if args.directories:
        directories = []
        for item in args.directories:
            path = Path(item)
            if not path.is_absolute():
                path = repo_root / path
            directories.append(path.resolve())
    else:
        sources = repo_root / 'sources'
        directories = sorted(p for p in sources.iterdir() if p.is_dir())

    total_merged = 0
    total_removed = 0

    for directory in directories:
        if not directory.is_dir():
            print(f'Ошибка: каталог не найден: {directory}', file=sys.stderr)
            sys.exit(1)

        print(f'--- {directory.relative_to(repo_root)} ---')
        merged, removed = process_directory(directory, args.dry_run)
        total_merged += merged
        total_removed += removed

    mode = ' (dry-run)' if args.dry_run else ''
    print(f'Итого{mode}: склеено групп {total_merged}, удалено частей {total_removed}')


if __name__ == '__main__':
    main()
