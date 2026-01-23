import os
import html


def _to_posix_path(path: str) -> str:
    """Конвертирует Windows путь в POSIX формат для HTML."""
    return path.replace("\\", "/")


def _build_items(project_root: str) -> dict[str, list[tuple[str, str]]]:
    """
    Возвращает словарь: имя_группы -> список (href, название_файла).
    Группа = имя подпапки в sources/ или 'root' для файлов в корне sources/.
    """
    sources_dir = os.path.join(project_root, "sources")
    groups: dict[str, list[tuple[str, str]]] = {}
    
    if not os.path.isdir(sources_dir):
        return groups

    for dirpath, _, filenames in os.walk(sources_dir):
        for filename in filenames:
            # Обрабатываем только .txt файлы
            if not filename.lower().endswith(".txt"):
                continue

            full_path = os.path.join(dirpath, filename)
            rel_path = os.path.relpath(full_path, project_root)
            rel_href = _to_posix_path(rel_path)

            # Определяем имя группы (папка относительно sources/)
            rel_dir = os.path.relpath(dirpath, sources_dir)
            if rel_dir == ".":
                group_name = "root"
            else:
                group_name = _to_posix_path(rel_dir)

            # Название файла без расширения
            file_title = os.path.splitext(filename)[0]

            if group_name not in groups:
                groups[group_name] = []
            
            groups[group_name].append((rel_href, file_title))

    return groups


def _render_li(href: str, title: str, indent: str = "        ") -> str:
    """Генерирует HTML элемент <li> со ссылкой."""
    safe_href = html.escape(href, quote=True)
    safe_title = html.escape(title, quote=False)
    return f'{indent}<li><a href="{safe_href}">{safe_title}</a></li>'


def _render_folder_li(group_name: str, indent: str = "        ") -> str:
    """Генерирует HTML элемент <li> для названия папки."""
    safe_name = html.escape(group_name, quote=False)
    return f'{indent}<li class="folder-name">{safe_name}'


def update_index_html(project_root: str) -> None:
    """Обновляет index.html списком ссылок на .txt файлы из sources/."""
    index_path = os.path.join(project_root, "index.html")
    
    try:
        with open(index_path, "r", encoding="utf-8") as f:
            index_html = f.read()
    except FileNotFoundError:
        print(f"Ошибка: файл {index_path} не найден")
        return

    groups = _build_items(project_root)
    
    # Строим HTML список
    lines = ["    <ul>"]
    
    # Сортируем группы по имени
    sorted_groups = sorted(groups.items(), key=lambda x: x[0])
    
    for group_name, items in sorted_groups:
        if group_name == "root":
            # Файлы в корне sources/ без вложенности
            for href, title in sorted(items, key=lambda x: x[1]):
                lines.append(_render_li(href, title, "        "))
        else:
            # Файлы в подпапках с вложенным списком
            lines.append(_render_folder_li(group_name, "        "))
            lines.append('            <ul>')
            for href, title in sorted(items, key=lambda x: x[1]):
                lines.append(_render_li(href, title, "                "))
            lines.append('            </ul>')
            lines.append('        </li>')
    
    lines.append("    </ul>")
    ul_block = "\n".join(lines)

    # Находим позицию после </h1> и заменяем содержимое до </body>
    h1_end_marker = '<h1>Список страниц</h1>'
    h1_pos = index_html.find(h1_end_marker)
    
    if h1_pos == -1:
        print("Ошибка: не найден заголовок '<h1>Список страниц</h1>' в index.html")
        return
    
    h1_end = h1_pos + len(h1_end_marker)
    body_end = index_html.find('</body>')
    
    if body_end == -1:
        print("Ошибка: не найден тег </body> в index.html")
        return
    
    # Заменяем содержимое между </h1> и </body>
    new_html = index_html[:h1_end] + "\n" + ul_block + "\n" + index_html[body_end:]
    
    with open(index_path, "w", encoding="utf-8") as f:
        f.write(new_html)
    
    print(f"Индекс обновлен: {len(groups)} групп, всего файлов: {sum(len(items) for items in groups.values())}")


def main() -> None:
    """Главная функция скрипта."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    update_index_html(project_root)


if __name__ == "__main__":
    main()
