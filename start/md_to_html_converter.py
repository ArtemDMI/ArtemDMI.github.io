import os
import html

def escape_html(text):
    """Escapes special HTML characters in a string."""
    return html.escape(text, quote=True)

def parse_md_file(filepath):
    """
    Parses an .md file, extracting Russian/English text pairs.
    Pairs are separated by '---'.
    """
    pairs = []
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            
        ru_line = None
        for line in lines:
            stripped_line = line.strip()
            if not stripped_line:
                continue

            if stripped_line == '---':
                ru_line = None
                continue

            if ru_line is None:
                ru_line = stripped_line
            else:
                en_line = stripped_line
                pairs.append((ru_line, en_line))
                ru_line = None # Reset for the next pair

    except FileNotFoundError:
        # Silently ignore if file not found, though the main logic should prevent this.
        pass
    return pairs

def equalize_pair_lengths(pairs):
    """
    Equalizes the length of strings in each pair by padding the shorter one with spaces.
    """
    equalized_pairs = []
    for ru, en in pairs:
        max_len = max(len(ru), len(en))
        # Using non-breaking space might be better for HTML rendering
        equalized_ru = ru.ljust(max_len)
        equalized_en = en.ljust(max_len)
        equalized_pairs.append((equalized_ru, equalized_en))
    return equalized_pairs

def generate_html(pairs, output_filename):
    """Generates an HTML file from a list of text pairs."""
    title = os.path.splitext(os.path.basename(output_filename))[0]
    
    html_content = f'''<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="utf-8">
    <title>{escape_html(title)}</title>
    <style>
        body {{
            background-color: #0f0f0f;
            color: #a5a5a5;
            font-family: system-ui, -apple-system, sans-serif;
            padding: 20px;
            margin: 0;
        }}
        .line {{
            cursor: pointer;
            /* margin-bottom: 8px; */ /* Removed to eliminate gaps */
            transition: background-color 0.2s;
            padding: 0 8px;
            border-radius: 4px;
            white-space: pre-wrap;
            margin-bottom: 1em; /* one empty line between items */
        }}
        .line:last-child {{
            margin-bottom: 0;
        }}
        .line:hover {{
            background-color: #1a1a1a;
        }}
        .line.lang-en {{
            color: palegreen;
        }}
    </style>
</head>
<body>
'''
    
    div_lines = []
    for ru_text, en_text in pairs:
        escaped_ru = escape_html(ru_text)
        escaped_en = escape_html(en_text)
        div_lines.append(f'    <div class="line" data-ru="{escaped_ru}" data-en="{escaped_en}">{escaped_ru}</div>')
    
    html_content += '\n'.join(div_lines)

    html_content += '''
    <script>
        document.addEventListener('DOMContentLoaded', () => {
            document.querySelectorAll('.line').forEach(element => {
                element.addEventListener('click', () => {
                    const ruText = element.getAttribute('data-ru');
                    const enText = element.getAttribute('data-en');
                    if (element.textContent === ruText) {
                        element.textContent = enText;
                        element.classList.add('lang-en');
                    } else {
                        element.textContent = ruText;
                        element.classList.remove('lang-en');
                    }
                });
            });
        });
    </script>
</body>
</html>
'''
    
    with open(output_filename, 'w', encoding='utf-8') as f:
        f.write(html_content)

def cleanup_orphaned_html_files():
    """
    Removes HTML files from 'pages' that don't have corresponding .md files in 'sources'.
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    
    sources_dir = os.path.join(project_root, 'sources')
    pages_dir = os.path.join(project_root, 'pages')

    if not os.path.isdir(pages_dir):
        return

    # Scan all HTML files in pages/
    for dirpath, _, filenames in os.walk(pages_dir):
        # Determine relative path to sources folder
        relative_path = os.path.relpath(dirpath, pages_dir)
        source_dir = os.path.join(sources_dir, relative_path)
        
        for filename in filenames:
            if filename.endswith('.html'):
                html_path = os.path.join(dirpath, filename)
                # Look for corresponding .md file
                md_filename = os.path.splitext(filename)[0] + '.md'
                md_path = os.path.join(source_dir, md_filename)
                
                # If .md file doesn't exist - remove HTML
                if not os.path.exists(md_path):
                    try:
                        os.remove(html_path)
                        print(f"Removed orphaned file: {html_path}")
                    except OSError as e:
                        print(f"Error removing {html_path}: {e}")

def process_all_files():
    """
    Processes all .md files in the 'sources' directory and its subdirectories
    that do not have a corresponding .html file in the 'pages' directory.
    """
    # Define paths relative to the script's location
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    
    sources_dir = os.path.join(project_root, 'sources')
    pages_dir = os.path.join(project_root, 'pages')

    if not os.path.isdir(sources_dir):
        return

    for dirpath, _, filenames in os.walk(sources_dir):
        # Create corresponding directory structure in 'pages'
        relative_path = os.path.relpath(dirpath, sources_dir)
        output_dir = os.path.join(pages_dir, relative_path)
        
        os.makedirs(output_dir, exist_ok=True)

        for filename in filenames:
            if filename.endswith('.md'):
                source_path = os.path.join(dirpath, filename)
                output_filename = os.path.splitext(filename)[0] + '.html'
                output_path = os.path.join(output_dir, output_filename)
                
                if not os.path.exists(output_path):
                    pairs = parse_md_file(source_path)
                    if pairs:
                        equalized_pairs = equalize_pair_lengths(pairs)
                        generate_html(equalized_pairs, output_path)

def main():
    """Main function to run the conversion process."""
    process_all_files()
    cleanup_orphaned_html_files()

if __name__ == '__main__':
    main()
