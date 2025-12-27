#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для извлечения текста субтитров из файлов.
Удаляет номера субтитров, таймеры и пустые строки,
оставляя только текст в одну строку через пробелы.
"""

import re
import os
from pathlib import Path


def is_timer_line(line):
    """Проверяет, является ли строка таймером (формат: 00:00:33,367 --> 00:00:34,368)"""
    timer_pattern = r'^\d{2}:\d{2}:\d{2}[,.]\d{3}\s*-->\s*\d{2}:\d{2}:\d{2}[,.]\d{3}$'
    return bool(re.match(timer_pattern, line.strip()))


def is_subtitle_number(line):
    """Проверяет, является ли строка только номером субтитра (только цифры)"""
    stripped = line.strip()
    return stripped.isdigit()


def is_already_processed(file_path):
    """
    Проверяет, является ли файл уже обработанным.
    Обработанный файл содержит разделитель '---' или не содержит паттерна субтитров.
    """
    print(f"  [ПРОВЕРКА] Начинаю проверку файла...")
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        print(f"  [ПРОВЕРКА] Ошибка при чтении файла для проверки: {e}")
        return False
    
    # Если файл пустой или очень короткий (меньше 10 символов), считаем обработанным
    if len(content.strip()) < 10:
        print(f"  [ПРОВЕРКА] Файл слишком короткий ({len(content)} символов), считаем обработанным")
        return True
    
    # Если файл содержит разделитель '---', значит он уже обработан
    if '---' in content:
        print(f"  [ПРОВЕРКА] Найден разделитель '---', файл уже обработан")
        return True
    
    # Проверяем наличие паттерна субтитров (номер → таймер)
    lines = content.split('\n')
    print(f"  [ПРОВЕРКА] Всего строк в файле: {len(lines)}")
    
    subtitle_pattern_found = False
    checked_lines = 0
    max_check = min(100, len(lines))  # Проверяем первые 100 строк для скорости
    
    for i in range(max_check):
        line = lines[i].strip()
        
        # Пропускаем пустые строки
        if not line:
            continue
        
        checked_lines += 1
        
        # Если нашли номер субтитра
        if line.isdigit():
            print(f"  [ПРОВЕРКА] Найдена строка с номером: '{line}' (строка {i+1})")
            # Проверяем следующую строку на таймер
            if i + 1 < len(lines):
                next_line = lines[i + 1].strip()
                if is_timer_line(next_line):
                    print(f"  [ПРОВЕРКА] Найден паттерн субтитров: номер '{line}' → таймер '{next_line}'")
                    subtitle_pattern_found = True
                    break
    
    if subtitle_pattern_found:
        print(f"  [ПРОВЕРКА] Файл содержит паттерн субтитров - НЕ обработан, требуется обработка")
        return False
    else:
        print(f"  [ПРОВЕРКА] Паттерн субтитров не найден (проверено {checked_lines} строк), файл уже обработан")
        return True


def extract_subtitle_text(file_path):
    """
    Извлекает текст субтитров из файла.
    Возвращает строку с текстом, разделенным пробелами.
    """
    print(f"  [ИЗВЛЕЧЕНИЕ] Начинаю извлечение текста...")
    text_lines = []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        print(f"  [ИЗВЛЕЧЕНИЕ] Прочитано строк: {len(lines)}")
    except Exception as e:
        print(f"  [ИЗВЛЕЧЕНИЕ] Ошибка при чтении файла {file_path}: {e}")
        return None
    
    subtitle_count = 0
    i = 0
    while i < len(lines):
        line = lines[i].rstrip('\n\r')
        
        # Пропускаем пустые строки
        if not line.strip():
            i += 1
            continue
        
        # Пропускаем номера субтитров
        if is_subtitle_number(line):
            subtitle_count += 1
            i += 1
            # Следующая строка должна быть таймером
            if i < len(lines):
                timer_line = lines[i].rstrip('\n\r')
                if is_timer_line(timer_line):
                    i += 1
                    # Теперь читаем текст до следующей пустой строки или следующего номера
                    while i < len(lines):
                        text_line = lines[i].rstrip('\n\r')
                        # Если пустая строка или следующий номер - прекращаем
                        if not text_line.strip() or is_subtitle_number(text_line):
                            break
                        # Если это не таймер - это текст субтитра
                        if not is_timer_line(text_line):
                            text_lines.append(text_line.strip())
                        i += 1
                    continue
        
        i += 1
    
    print(f"  [ИЗВЛЕЧЕНИЕ] Найдено субтитров: {subtitle_count}, текстовых строк: {len(text_lines)}")
    
    # Собираем все текстовые строки в одну через пробелы
    result = ' '.join(text_lines)
    print(f"  [ИЗВЛЕЧЕНИЕ] Итоговая длина текста: {len(result)} символов")
    return result


def collect_files_from_path(path_str, script_dir):
    """
    Собирает список файлов для обработки из пути (файл или папка).
    Возвращает список Path объектов.
    """
    # Обрабатываем абсолютные и относительные пути
    if os.path.isabs(path_str):
        path = Path(path_str)
    else:
        path = script_dir / path_str
    
    if not path.exists():
        print(f"  [ОШИБКА] Путь не найден: {path}")
        return []
    
    files_to_process = []
    
    if path.is_file():
        # Это файл - добавляем его
        print(f"  [ИНФО] Найден файл: {path}")
        files_to_process.append(path)
    elif path.is_dir():
        # Это папка - находим все .md файлы в ней
        print(f"  [ИНФО] Найдена папка: {path}")
        md_files = list(path.glob('*.md'))
        print(f"  [ИНФО] Найдено .md файлов в папке: {len(md_files)}")
        files_to_process.extend(md_files)
    else:
        print(f"  [ОШИБКА] Неизвестный тип пути: {path}")
    
    return files_to_process


def process_single_file(file_path, idx, total):
    """
    Обрабатывает один файл.
    """
    print(f"\n[{idx}/{total}] Обработка файла: {file_path.name}")
    print(f"  [ИНФО] Полный путь: {file_path}")
    
    if not file_path.exists():
        print(f"  [ОШИБКА] Файл не найден: {file_path}")
        return False
    
    try:
        file_size = file_path.stat().st_size
        print(f"  [ИНФО] Размер файла: {file_size} байт")
    except Exception as e:
        print(f"  [ОШИБКА] Не удалось получить размер файла: {e}")
        return False
    
    # Проверяем, не обработан ли файл уже
    if is_already_processed(file_path):
        print(f"  [РЕЗУЛЬТАТ] Файл уже обработан, пропускаем")
        return False
    
    # Извлекаем текст
    extracted_text = extract_subtitle_text(file_path)
    
    if extracted_text is None:
        print(f"  [ОШИБКА] Пропущен из-за ошибки при извлечении")
        return False
    
    if not extracted_text.strip():
        print(f"  [ПРЕДУПРЕЖДЕНИЕ] Извлеченный текст пуст!")
        return False
    
    # Записываем результат обратно в файл
    print(f"  [ЗАПИСЬ] Записываю результат в файл...")
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(extracted_text)
        print(f"  [РЕЗУЛЬТАТ] ✓ Готово! Извлечено {len(extracted_text)} символов")
        return True
    except Exception as e:
        print(f"  [ОШИБКА] Ошибка при записи: {e}")
        return False


def process_files(list_file_path):
    """
    Обрабатывает файлы и папки из списка.
    """
    script_dir = Path(list_file_path).parent
    
    # Читаем список путей (файлы или папки)
    try:
        with open(list_file_path, 'r', encoding='utf-8') as f:
            paths = [line.strip() for line in f if line.strip()]
    except Exception as e:
        print(f"Ошибка при чтении списка файлов {list_file_path}: {e}")
        return
    
    print(f"[НАЧАЛО] Найдено путей в списке: {len(paths)}")
    print("=" * 60)
    
    # Собираем все файлы для обработки
    all_files = []
    for path_str in paths:
        print(f"\n[СБОР] Обработка пути: {path_str}")
        print("-" * 60)
        files = collect_files_from_path(path_str, script_dir)
        all_files.extend(files)
    
    print(f"\n[НАЧАЛО ОБРАБОТКИ] Всего файлов для обработки: {len(all_files)}")
    print("=" * 60)
    
    if not all_files:
        print("[ПРЕДУПРЕЖДЕНИЕ] Не найдено файлов для обработки!")
        return
    
    # Обрабатываем каждый файл
    processed_count = 0
    skipped_count = 0
    error_count = 0
    
    for idx, file_path in enumerate(all_files, 1):
        result = process_single_file(file_path, idx, len(all_files))
        if result:
            processed_count += 1
        elif file_path.exists():
            skipped_count += 1
        else:
            error_count += 1
    
    print("\n" + "=" * 60)
    print(f"[ЗАВЕРШЕНО] Обработка завершена")
    print(f"  Обработано: {processed_count}")
    print(f"  Пропущено: {skipped_count}")
    print(f"  Ошибок: {error_count}")
    print("=" * 60)


if __name__ == '__main__':
    # Путь к файлу со списком относительно скрипта
    script_dir = Path(__file__).parent
    list_file = script_dir / 'list.md'
    
    if not list_file.exists():
        print(f"Файл списка не найден: {list_file}")
    else:
        process_files(list_file)

