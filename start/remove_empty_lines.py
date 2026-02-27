#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Удаляет пустые строки (и строки только из пробелов) в файлах переводов.
Приводит одиночные строки с тире к двум строкам (схема translate-02-eng).
Использование: python remove_empty_lines.py [файл1 файл2 ...]
Без аргументов обрабатывает список файлов по умолчанию.
"""

import sys
from pathlib import Path

# Для вывода имён файлов с кириллицей в консоль Windows
try:
    if sys.stdout.encoding and "utf" not in sys.stdout.encoding.lower():
        sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


def _expand_single_dash_runs(lines: list[str]) -> list[str]:
    """
    Заменяет каждую серию ровно из одной строки '-' на две строки '-',
    чтобы следовать схеме translate-02-eng (между блоками — не одна, а две строки с тире).
    """
    result: list[str] = []
    i = 0
    while i < len(lines):
        if lines[i].strip() == "-":
            run_end = i
            while run_end < len(lines) and lines[run_end].strip() == "-":
                run_end += 1
            run_len = run_end - i
            if run_len == 1:
                result.append("-")
                result.append("-")
            else:
                result.extend(lines[i:run_end])
            i = run_end
        else:
            result.append(lines[i])
            i += 1
    return result


def remove_empty_lines(path: Path) -> tuple[bool, int, int]:
    """
    Читает файл: удаляет пустые/пробельные строки, расширяет одиночные '-' до двух.
    Возвращает (успех, удалено пустых, добавлено тире).
    """
    try:
        raw = path.read_text(encoding="utf-8")
    except Exception as e:
        print(f"Ошибка чтения {path}: {e}", file=sys.stderr)
        return False, 0, 0

    lines = raw.splitlines(keepends=False)
    newline = "\r\n" if "\r\n" in raw else "\n"

    non_empty = [line for line in lines if line.strip() != ""]
    removed_empty = len(lines) - len(non_empty)

    normalized = _expand_single_dash_runs(non_empty)
    dash_added = len(normalized) - len(non_empty)

    if removed_empty == 0 and dash_added == 0:
        return True, 0, 0

    try:
        path.write_text(newline.join(normalized) + (newline if normalized else ""), encoding="utf-8")
    except Exception as e:
        print(f"Ошибка записи {path}: {e}", file=sys.stderr)
        return False, 0, 0

    return True, removed_empty, dash_added


def main():
    root = Path(__file__).resolve().parent.parent
    if len(sys.argv) < 2:
        default_files = [
            "sources/08/tmp.txt",
            "sources/08/tmpS001.txt",
            "sources/08/tmpS002.txt",
            "sources/08/tmpS003.txt",
            "sources/08/tmpS004.txt",
            "sources/08/tmpS005.txt",
            "sources/08/tmpS006.txt",
            "sources/09/The_Devils_-_Joe_AbercrombieS001.txt",
            "sources/09/The_Devils_-_Joe_AbercrombieS002.txt",
            "sources/09/The_Devils_-_Joe_AbercrombieS003.txt",
            "sources/09/The_Devils_-_Joe_AbercrombieS004.txt",
            "sources/09/The_Devils_-_Joe_AbercrombieS005.txt",
            "sources/12_couz/Союз трехS001.txt",
            "sources/10/Narrow.txt",
            "sources/10/NarrowS001.txt",
            "sources/10/NarrowS002.txt",
            "sources/10/NarrowS003.txt",
            "sources/10/Kesam.txt",
            "sources/10/KesamS001.txt",
            "sources/10/KesamS002.txt",
            "sources/10/KesamS003.txt",
            "sources/10/Island.txt",
            "sources/10/IslandS001.txt",
            "sources/10/IslandS002.txt",
            "sources/10/IslandS003.txt",
        ]
        paths = [root / f for f in default_files]
    else:
        paths = [Path(p).resolve() for p in sys.argv[1:]]

    ok = 0
    total_removed = 0
    total_dash_added = 0
    for path in paths:
        if not path.exists():
            print(f"skip (not found): {path}")
            continue
        success, removed, dash_added = remove_empty_lines(path)
        if success:
            ok += 1
            if removed > 0 or dash_added > 0:
                parts = []
                if removed > 0:
                    parts.append(f"removed {removed}")
                if dash_added > 0:
                    parts.append(f"dash+{dash_added}")
                print(f"OK ({', '.join(parts)}): {path.name}")
            else:
                print(f"unchanged: {path.name}")
            total_removed += removed
            total_dash_added += dash_added
        else:
            print(f"error: {path}")

    print(f"\nDone. Processed: {ok}/{len(paths)}, empty removed: {total_removed}, dash lines added: {total_dash_added}")


if __name__ == "__main__":
    main()
