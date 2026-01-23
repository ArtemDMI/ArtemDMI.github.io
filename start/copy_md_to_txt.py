import os
import shutil

def copy_md_to_txt():
    """
    Копирует все .md файлы из sources/05 и создает их копии с расширением .txt
    """
    # Определяем пути относительно расположения скрипта
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    
    sources_dir = os.path.join(project_root, 'sources', '05')
    
    if not os.path.isdir(sources_dir):
        print(f"Ошибка: папка {sources_dir} не найдена")
        return
    
    # Получаем список всех .md файлов
    md_files = [f for f in os.listdir(sources_dir) if f.endswith('.md')]
    
    if not md_files:
        print(f"В папке {sources_dir} не найдено .md файлов")
        return
    
    copied_count = 0
    for md_file in md_files:
        source_path = os.path.join(sources_dir, md_file)
        # Создаем имя файла с расширением .txt
        txt_file = os.path.splitext(md_file)[0] + '.txt'
        dest_path = os.path.join(sources_dir, txt_file)
        
        try:
            # Копируем файл с новым расширением
            shutil.copy2(source_path, dest_path)
            print(f"Скопировано: {md_file} -> {txt_file}")
            copied_count += 1
        except Exception as e:
            print(f"Ошибка при копировании {md_file}: {e}")
    
    print(f"\nГотово! Скопировано файлов: {copied_count}")

if __name__ == '__main__':
    copy_md_to_txt()
