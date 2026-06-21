"""Чтение API-ключа только из файла по абсолютному пути."""

from pathlib import Path

# Единственный источник ключа — файл на диске, никуда не копируем.
API_KEY_PATH = Path(r"c:\PROJECTS\MALI\personal\KKK\cursor_ir_api.txt")


def load_api_key() -> str:
    if not API_KEY_PATH.is_file():
        raise FileNotFoundError(f"Файл ключа не найден: {API_KEY_PATH}")
    key = API_KEY_PATH.read_text(encoding="utf-8").strip()
    if not key:
        raise ValueError(f"Файл ключа пуст: {API_KEY_PATH}")
    return key
