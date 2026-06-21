import os
import html


def _to_posix_path(path: str) -> str:
    """Convert Windows path to POSIX format for HTML."""
    return path.replace("\\", "/")


def _build_items(project_root: str) -> dict[str, list[tuple[str, str]]]:
    """
    group_name -> list of (href, file_title) for all .txt under sources/.
    Group = direct subfolder of sources/ or 'root' for files in sources/ root.
    """
    sources_dir = os.path.join(project_root, "sources")
    groups: dict[str, list[tuple[str, str]]] = {}

    if not os.path.isdir(sources_dir):
        return groups

    for dirpath, _, filenames in os.walk(sources_dir):
        for filename in filenames:
            if not filename.lower().endswith(".txt"):
                continue

            full_path = os.path.join(dirpath, filename)
            rel_dir = os.path.relpath(dirpath, sources_dir)
            group_name = "root" if rel_dir == "." else _to_posix_path(rel_dir)
            file_title = os.path.splitext(filename)[0]

            rel_path = os.path.relpath(full_path, project_root)
            rel_href = _to_posix_path(rel_path)
            if group_name not in groups:
                groups[group_name] = []
            groups[group_name].append((rel_href, file_title))

    return groups


def _render_li(href: str, title: str, indent: str = "        ") -> str:
    """Generate HTML <li> with link."""
    safe_href = html.escape(href, quote=True)
    safe_title = html.escape(title, quote=False)
    return f'{indent}<li><a href="{safe_href}">{safe_title}</a></li>'


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
    """Update index.html with list of links to .txt files from sources/."""
    index_path = os.path.join(project_root, "index.html")

    try:
        with open(index_path, "r", encoding="utf-8") as f:
            index_html = f.read()
    except FileNotFoundError:
        print(f"[ERROR] Error: file not found: {index_path}")
        return

    groups = _build_items(project_root)

    pages_dir = os.path.join(project_root, "Pages")
    os.makedirs(pages_dir, exist_ok=True)

    # Remove Pages/*.html for which sources/<name> no longer exists
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

    # Generate Pages/<name>.html only for non-root groups that have at least one file
    pages_written = 0
    for group_name, items in groups.items():
        if group_name == "root" or len(items) == 0:
            continue
        _write_page_html(project_root, group_name, items)
        pages_written += 1

    # index.html contains only links to Pages/<name>.html (one per non-empty folder)
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


def main() -> None:
    """Entry point."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    update_index_html(project_root)


if __name__ == "__main__":
    main()
