import os
import re
import html


def _to_posix_path(path: str) -> str:
    return path.replace("\\", "/")


def _extract_first_ru_text(html_content: str) -> str | None:
    """
    Extracts the first Russian line from generated pages (first data-ru="...").
    Returns unescaped text, or None if not found.
    """
    m = re.search(r'data-ru="([^"]+)"', html_content)
    if not m:
        return None
    return html.unescape(m.group(1)).strip()


def _title_from_ru_text(ru_text: str, max_words: int = 4) -> str:
    # collapse whitespace to single spaces
    text = " ".join(ru_text.split())
    if not text:
        return ""
    words = text.split(" ")
    return " ".join(words[:max_words])


def _build_items(project_root: str) -> list[tuple[str, str]]:
    pages_dir = os.path.join(project_root, "pages")
    items: list[tuple[str, str]] = []
    if not os.path.isdir(pages_dir):
        return items

    for dirpath, _, filenames in os.walk(pages_dir):
        for filename in filenames:
            if not filename.lower().endswith(".html"):
                continue

            full_path = os.path.join(dirpath, filename)
            rel_path = os.path.relpath(full_path, project_root)
            rel_href = _to_posix_path(rel_path)

            try:
                with open(full_path, "r", encoding="utf-8") as f:
                    content = f.read()
            except OSError:
                continue

            ru = _extract_first_ru_text(content)
            title = _title_from_ru_text(ru or "") if ru else ""
            if not title:
                title = os.path.splitext(filename)[0]

            items.append((rel_href, title))

    items.sort(key=lambda x: x[0])
    return items


def _render_li(href: str, title: str) -> str:
    safe_href = html.escape(href, quote=True)
    safe_title = html.escape(title, quote=False)
    return f'        <li><a href="{safe_href}">{safe_title}</a></li>'


def update_index_html(project_root: str) -> None:
    index_path = os.path.join(project_root, "index.html")
    try:
        with open(index_path, "r", encoding="utf-8") as f:
            index_html = f.read()
    except FileNotFoundError:
        return

    items = _build_items(project_root)
    ul_block = "<ul>\n" + "\n".join(_render_li(href, title) for href, title in items) + "\n    </ul>"

    # Replace the first <ul>...</ul> block
    new_html, n = re.subn(r"<ul>[\s\S]*?</ul>", ul_block, index_html, count=1)
    if n == 0:
        # If no <ul> exists, insert after <h1> (best effort)
        new_html = re.sub(r"(</h1>\s*)", r"\1    " + ul_block + "\n", index_html, count=1)

    with open(index_path, "w", encoding="utf-8") as f:
        f.write(new_html)


def main() -> None:
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    update_index_html(project_root)


if __name__ == "__main__":
    main()


