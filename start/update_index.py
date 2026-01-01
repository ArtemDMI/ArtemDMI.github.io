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


def _title_from_ru_text(ru_text: str) -> str:
    # collapse whitespace to single spaces
    text = " ".join(ru_text.split())
    if not text:
        return ""
    
    # Find first punctuation mark: . , ! ? : ; — –
    match = re.search(r'[,.!?:;—–]', text)
    
    if match:
        end_pos = match.start()
        # If punctuation is before 50 chars, we need at least 50 chars
        if end_pos < 50:
            # Find first punctuation after 50 chars
            next_match = re.search(r'[,.!?:;—–]', text[50:])
            if next_match:
                end_pos = 50 + next_match.start()
            else:
                # No punctuation after 50, take 50 chars or until end if shorter
                end_pos = min(50, len(text))
        return text[:end_pos].strip()
    
    # No punctuation found, return first 50 chars or all text if shorter
    if len(text) > 50:
        return text[:50].strip()
    return text


def _build_items(project_root: str) -> dict[str, tuple[float, list[tuple[str, str]]]]:
    """
    Returns dict mapping group_name to (mtime, items_list).
    mtime is the modification time of the folder (oldest file in folder).
    """
    pages_dir = os.path.join(project_root, "pages")
    groups: dict[str, tuple[float, list[tuple[str, str]]]] = {}
    if not os.path.isdir(pages_dir):
        return groups

    for dirpath, _, filenames in os.walk(pages_dir):
        for filename in filenames:
            if not filename.lower().endswith(".html"):
                continue

            full_path = os.path.join(dirpath, filename)
            rel_path = os.path.relpath(full_path, project_root)
            rel_href = _to_posix_path(rel_path)

            # Determine group name (folder relative to pages/)
            rel_dir = os.path.relpath(dirpath, pages_dir)
            if rel_dir == ".":
                group_name = "root"
            else:
                group_name = _to_posix_path(rel_dir)

            try:
                file_mtime = os.path.getmtime(full_path)
                # Get folder creation/modification time
                dir_mtime = os.path.getmtime(dirpath)
                with open(full_path, "r", encoding="utf-8") as f:
                    content = f.read()
            except OSError:
                continue

            ru = _extract_first_ru_text(content)
            file_name = os.path.splitext(filename)[0]  # имя файла без расширения
            ru_title = _title_from_ru_text(ru or "") if ru else ""
            if ru_title:
                title = f"{file_name} - {ru_title}"
            else:
                title = file_name

            if group_name not in groups:
                # Use folder modification time (oldest file mtime in folder)
                groups[group_name] = (min(file_mtime, dir_mtime), [])
            else:
                # Update mtime to oldest file in folder
                old_mtime, items = groups[group_name]
                groups[group_name] = (min(old_mtime, file_mtime, dir_mtime), items)
            
            groups[group_name][1].append((rel_href, title))

    return groups


def _render_li(href: str, title: str, indent: str = "        ") -> str:
    safe_href = html.escape(href, quote=True)
    safe_title = html.escape(title, quote=False)
    return f'{indent}<li><a href="{safe_href}">{safe_title}</a></li>'


def _render_folder_li(group_name: str, indent: str = "        ") -> str:
    safe_name = html.escape(group_name, quote=False)
    return f'{indent}<li class="folder-name">{safe_name}'


def update_index_html(project_root: str) -> None:
    index_path = os.path.join(project_root, "index.html")
    try:
        with open(index_path, "r", encoding="utf-8") as f:
            index_html = f.read()
    except FileNotFoundError:
        return

    groups = _build_items(project_root)
    
    # Build the list HTML
    lines = ["    <ul>"]
    # Sort groups by modification time (oldest first), then by name
    sorted_groups = sorted(groups.items(), key=lambda x: (x[1][0], x[0]))
    
    for group_name, (_, items) in sorted_groups:
        if group_name == "root":
            for href, title in sorted(items, key=lambda x: x[0]):
                lines.append(_render_li(href, title, "        "))
        else:
            lines.append(_render_folder_li(group_name, "        "))
            lines.append('            <ul>')
            for href, title in sorted(items, key=lambda x: x[0]):
                lines.append(_render_li(href, title, "                "))
            lines.append('            </ul>')
            lines.append('        </li>')
    lines.append("    </ul>")
    ul_block = "\n".join(lines)

    # Ensure CSS for folder names exists
    folder_style = """        .folder-name {
            font-size: 48px;
            font-weight: bold;
            margin-top: 20px;
            margin-bottom: 10px;
        }"""
    
    nested_list_style = """        ul ul li {
            margin-bottom: 2px;
            width: fit-content;
        }"""
    
    # Add or update folder-name style in CSS
    if '.folder-name' not in index_html:
        # Insert before closing </style>
        index_html = re.sub(r'(\n)([ \t]*</style>)', r'\1' + folder_style + r'\n\2', index_html, count=1)
    else:
        # Replace existing folder-name style - match any whitespace before .folder-name
        # Use multiline pattern to match across lines
        pattern = r'[ \t]*\.folder-name\s*\{[^}]*\}'
        index_html = re.sub(pattern, folder_style, index_html, count=1, flags=re.MULTILINE | re.DOTALL)
    
    # Ensure nested list item style exists
    if 'ul ul li' not in index_html:
        # Add nested list style if not present
        index_html = re.sub(r'(\n)([ \t]*</style>)', r'\1' + nested_list_style + r'\n\2', index_html, count=1)
    else:
        # Remove all existing ul ul li styles and extra blank lines
        index_html = re.sub(r'[ \t]*ul ul li\s*\{[^}]*\}\n*', '', index_html, flags=re.MULTILINE | re.DOTALL)
        # Add single style before </style>
        index_html = re.sub(r'(\n)([ \t]*</style>)', r'\1' + nested_list_style + r'\n\2', index_html, count=1)

    # Replace everything between </h1> and last </ul> in body
    # Find the position after <h1>Список страниц</h1>
    h1_match = re.search(r'<h1>Список страниц</h1>', index_html)
    if h1_match:
        h1_end = h1_match.end()
        # Find the last </ul> before </body>
        body_end = index_html.find('</body>')
        if body_end == -1:
            body_end = len(index_html)
        
        # Find last </ul> before </body>
        last_ul_end = index_html.rfind('</ul>', h1_end, body_end)
        if last_ul_end != -1:
            # Replace everything from after </h1> to last </ul>
            new_html = index_html[:h1_end] + "\n" + ul_block + index_html[last_ul_end + 5:]
            with open(index_path, "w", encoding="utf-8") as f:
                f.write(new_html)
            return
    
    # Fallback: try simple replacement
    pattern = r'(<h1>Список страниц</h1>\s*)<ul>[\s\S]*?</ul>'
    new_html = re.sub(pattern, r'\1' + ul_block, index_html, flags=re.DOTALL)
    
    if new_html == index_html:
        # Last resort: replace everything between first <ul> and last </ul>
        first_ul = index_html.find('<ul>')
        last_ul_end = index_html.rfind('</ul>')
        if first_ul != -1 and last_ul_end != -1:
            new_html = index_html[:first_ul] + ul_block + index_html[last_ul_end + 5:]

    with open(index_path, "w", encoding="utf-8") as f:
        f.write(new_html)


def main() -> None:
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    update_index_html(project_root)


if __name__ == "__main__":
    main()


