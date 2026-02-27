import os
import re
import html
from collections import defaultdict


def _to_posix_path(path: str) -> str:
    """Convert Windows path to POSIX format for HTML."""
    return path.replace("\\", "/")


def _is_dash_separator(line: str) -> bool:
    """True if line after strip() is non-empty and consists only of '-'."""
    s = line.strip()
    return bool(s) and all(c == "-" for c in s)


def _split_by_dash_separators(lines: list[str]) -> list[str]:
    """
    Split lines into segments: content between runs of dash-only lines.
    One or more consecutive dash lines count as a single separator (not included in segments).
    """
    segments: list[str] = []
    current: list[str] = []
    i = 0
    while i < len(lines):
        if _is_dash_separator(lines[i]):
            segments.append("\n".join(current))
            current = []
            while i < len(lines) and _is_dash_separator(lines[i]):
                i += 1
            continue
        current.append(lines[i])
        i += 1
    segments.append("\n".join(current))
    return segments


def file_passes_bilingual_pattern(file_path: str) -> bool:
    """
    True if file has full bilingual structure: segments alternate RU/EN between
    dash separators, and every English segment (indices 2, 4, 6, ...) is non-empty.
    Files with empty English slots are excluded from index and Pages.
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.read().splitlines()
    except (OSError, UnicodeDecodeError):
        return False
    segments = _split_by_dash_separators(lines)
    if len(segments) < 3:
        return False
    for i in range(2, len(segments), 2):
        if not segments[i].strip():
            return False
    return True


def _build_items(project_root: str) -> tuple[dict[str, list[tuple[str, str]]], list[tuple[str, str]]]:
    """
    Returns (groups, excluded).
    groups: group_name -> list of (href, file_title) for .txt that pass bilingual pattern.
    excluded: list of (group_name, stem) for .txt that did not pass (missing/empty English segments).
    Group = direct subfolder of sources/ or 'root' for files in sources/ root.
    """
    sources_dir = os.path.join(project_root, "sources")
    groups: dict[str, list[tuple[str, str]]] = {}
    excluded: list[tuple[str, str]] = []

    if not os.path.isdir(sources_dir):
        return groups, excluded

    for dirpath, _, filenames in os.walk(sources_dir):
        for filename in filenames:
            if not filename.lower().endswith(".txt"):
                continue

            full_path = os.path.join(dirpath, filename)
            rel_dir = os.path.relpath(dirpath, sources_dir)
            group_name = "root" if rel_dir == "." else _to_posix_path(rel_dir)
            file_title = os.path.splitext(filename)[0]

            if not file_passes_bilingual_pattern(full_path):
                excluded.append((group_name, file_title))
                continue

            rel_path = os.path.relpath(full_path, project_root)
            rel_href = _to_posix_path(rel_path)
            if group_name not in groups:
                groups[group_name] = []
            groups[group_name].append((rel_href, file_title))

    return groups, excluded


def _excluded_to_paths(excluded: list[tuple[str, str]]) -> list[str]:
    """Convert (group_name, stem) to POSIX paths for sources/.gitignore (group/stem.txt or stem.txt)."""
    paths: list[str] = []
    for group_name, stem in excluded:
        if group_name == "root":
            paths.append(f"{stem}.txt")
        else:
            paths.append(f"{group_name}/{stem}.txt")
    return sorted(paths)


def _update_gitignore(project_root: str, excluded: list[tuple[str, str]]) -> int:
    """
    Обновляет sources/.gitignore: только список исключённых путей, по одному на строку, без комментариев.
    """
    gitignore_path = os.path.join(project_root, "sources", ".gitignore")
    new_paths = _excluded_to_paths(excluded)
    content = "\n".join(new_paths) + ("\n" if new_paths else "")
    with open(gitignore_path, "w", encoding="utf-8") as f:
        f.write(content)
    return len(new_paths)


def _format_unable_links(excluded: list[tuple[str, str]]) -> str:
    """
    Format excluded (group_name, stem) list for console: compress consecutive stems
    with same base and trailing digits (e.g. tmpS006, tmpS007, tmpS008 -> tmpS006-008).
    """
    if not excluded:
        return "(none)"
    stem_digits_re = re.compile(r"^(.+?)(\d+)$")
    by_key: dict[tuple[str, str], list[tuple[int, int]]] = defaultdict(list)  # (group, base) -> [(num, pad_len)]
    no_digits: list[tuple[str, str]] = []  # (group, stem) for stems without trailing digits
    for group_name, stem in excluded:
        m = stem_digits_re.match(stem)
        if m:
            base, digits = m.group(1), m.group(2)
            by_key[(group_name, base)].append((int(digits), len(digits)))
        else:
            no_digits.append((group_name, stem))
    parts: list[str] = []
    for (group_name, base), nums_list in sorted(by_key.items()):
        nums_list.sort(key=lambda x: x[0])
        nums = [n for n, _ in nums_list]
        pad = max(p for _, p in nums_list)
        if len(nums) > 1 and all(nums[i] == nums[i - 1] + 1 for i in range(1, len(nums))):
            parts.append(f"{group_name}/{base}{str(nums[0]).zfill(pad)}-{str(nums[-1]).zfill(pad)}")
        else:
            for num, pl in nums_list:
                parts.append(f"{group_name}/{base}{str(num).zfill(pl)}")
    for group_name, stem in sorted(no_digits):
        parts.append(f"{group_name}/{stem}")
    return ", ".join(parts)


def _render_li(href: str, title: str, indent: str = "        ") -> str:
    """Generate HTML <li> with link."""
    safe_href = html.escape(href, quote=True)
    safe_title = html.escape(title, quote=False)
    return f'{indent}<li><a href="{safe_href}">{safe_title}</a></li>'


def _render_folder_li(group_name: str, indent: str = "        ") -> str:
    """Generate HTML <li> for folder name."""
    safe_name = html.escape(group_name, quote=False)
    return f'{indent}<li class="folder-name">{safe_name}'


def _pages_html_template() -> str:
    """Return HTML template (head + opening body) matching index.html style."""
    return """<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="utf-8">
    <title>{title}</title>
    <style>
        body {{ background-color: #0f0f0f; color: #a5a5a5; font-family: system-ui, -apple-system, sans-serif; padding: 40px; margin: 0; }}
        h1 {{ color: #ffffff; margin-bottom: 30px; }}
        ul {{ list-style: none; padding: 0; }}
        li {{ margin-bottom: 10px; }}
        a {{ color: #4a9eff; text-decoration: none; font-size: 16px; }}
        a:hover {{ color: #6bb3ff; text-decoration: underline; }}
    </style>
</head>
<body>
    <h1>{h1}</h1>
    <ul>
"""


def _write_page_html(project_root: str, group_name: str, items: list[tuple[str, str]]) -> None:
    """
    Write Pages/<group_name>.html with same style as index: heading = group_name, <ul> of links.
    href in items is relative to project root (e.g. sources/08/file.txt); from Pages/ we use ../sources/...
    """
    pages_dir = os.path.join(project_root, "Pages")
    os.makedirs(pages_dir, exist_ok=True)
    page_path = os.path.join(pages_dir, f"{group_name}.html")
    safe_h1 = html.escape(group_name, quote=False)
    title = html.escape(group_name, quote=True)
    parts = [_pages_html_template().format(title=title, h1=safe_h1)]
    for href, file_title in sorted(items, key=lambda x: x[1]):
        # From Pages/<name>.html to sources/... -> ../sources/...
        href_from_page = ".." + "/" + href if not href.startswith("/") else href
        safe_href = html.escape(href_from_page, quote=True)
        safe_title = html.escape(file_title, quote=False)
        parts.append(f'        <li><a href="{safe_href}">{safe_title}</a></li>\n')
    parts.append("    </ul>\n</body>\n</html>\n")
    with open(page_path, "w", encoding="utf-8") as f:
        f.write("".join(parts))


def update_index_html(project_root: str) -> None:
    """Update index.html with list of links to .txt files from sources/ (only files passing bilingual pattern)."""
    index_path = os.path.join(project_root, "index.html")

    try:
        with open(index_path, "r", encoding="utf-8") as f:
            index_html = f.read()
    except FileNotFoundError:
        print(f"[ERROR] Error: file not found: {index_path}")
        return

    groups, excluded = _build_items(project_root)

    pages_dir = os.path.join(project_root, "Pages")
    os.makedirs(pages_dir, exist_ok=True)

    # Step 4: remove Pages/*.html for which sources/<name> no longer exists
    sources_dir = os.path.join(project_root, "sources")
    valid_subdirs = set()
    if os.path.isdir(sources_dir):
        for name in os.listdir(sources_dir):
            if os.path.isdir(os.path.join(sources_dir, name)):
                valid_subdirs.add(name)
    for filename in os.listdir(pages_dir):
        if filename.endswith(".html"):
            stem = filename[:-5]
            if stem not in valid_subdirs:
                path = os.path.join(pages_dir, filename)
                os.remove(path)
                print(f"[INFO] Removed obsolete page: Pages/{filename} (no sources/{stem})")

    # Step 2: generate Pages/<name>.html only for non-root groups that have at least one file
    pages_written = 0
    for group_name, items in groups.items():
        if group_name == "root" or len(items) == 0:
            continue
        _write_page_html(project_root, group_name, items)
        pages_written += 1

    # Step 3: index.html contains only links to Pages/<name>.html (one per non-empty folder)
    lines = ["    <ul>"]
    sorted_groups = sorted(groups.items(), key=lambda x: x[0])
    for group_name, items in sorted_groups:
        if group_name == "root" or len(items) == 0:
            continue
        page_href = _to_posix_path(os.path.join("Pages", f"{group_name}.html"))
        lines.append(_render_li(page_href, group_name, "        "))
    lines.append("    </ul>")
    ul_block = "\n".join(lines)

    h1_end_marker = '<h1>Список страниц</h1>'
    h1_pos = index_html.find(h1_end_marker)
    if h1_pos == -1:
        print("[ERROR] Error: marker '<h1>Список страниц</h1>' not found in index.html")
        return
    h1_end = h1_pos + len(h1_end_marker)
    body_end = index_html.find("</body>")
    if body_end == -1:
        print("[ERROR] Error: </body> tag not found in index.html")
        return

    new_html = index_html[:h1_end] + "\n" + ul_block + "\n" + index_html[body_end:]
    with open(index_path, "w", encoding="utf-8") as f:
        f.write(new_html)

    total = sum(len(items) for items in groups.values())
    print(f"[INFO] Index updated: {len(groups)} groups, {total} files included. Pages written: {pages_written}.")
    if excluded:
        print("[INFO] List unable links:", _format_unable_links(excluded))

    excluded_count = _update_gitignore(project_root, excluded)
    if excluded_count > 0:
        print(f"[INFO] sources/.gitignore updated: {excluded_count} excluded paths.")


def main() -> None:
    """Entry point."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    update_index_html(project_root)


if __name__ == "__main__":
    main()
