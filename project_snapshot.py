import os
import json
import zipfile
from datetime import datetime
from pathlib import Path
import sys


def get_folder_structure(path: Path, prefix: str = "", max_depth: int = 3, current_depth: int = 0) -> str:
    """Рекурсивно собирает структуру папок"""
    if current_depth > max_depth:
        return ""

    result = ""
    items = sorted(path.iterdir(), key=lambda x: (not x.is_dir(), x.name))

    for i, item in enumerate(items):
        if item.name.startswith('.') or item.name == '__pycache__' or item.name == 'venv' or item.name == 'workspace':
            continue

        is_last = i == len(items) - 1
        result += f"{prefix}{'└── ' if is_last else '├── '}{item.name}{'/' if item.is_dir() else ''}\n"

        if item.is_dir():
            extension = "    " if is_last else "│   "
            result += get_folder_structure(item, prefix + extension, max_depth, current_depth + 1)

    return result


def get_file_content(file_path: Path) -> str:
    """Читает полное содержимое файла"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        return f"Ошибка чтения: {e}"


def collect_all_files(base_path: Path) -> list:
    """Собирает все файлы проекта (кроме мусора)"""
    all_files = []

    exclude_dirs = ['__pycache__', 'venv', '.git', 'workspace', 'session_logs', 'dialog_history']
    exclude_extensions = ['.pyc', '.pyo', '.log', '.db', '.sqlite3']

    for file_path in base_path.rglob('*'):
        if file_path.is_file():
            # Проверяем исключения
            if any(ex in str(file_path) for ex in exclude_dirs):
                continue
            if file_path.suffix in exclude_extensions:
                continue
            if file_path.name.startswith('.'):
                continue

            all_files.append(file_path)

    return all_files


def create_snapshot():
    """Создает два формата снимка проекта"""

    base_path = Path(__file__).parent
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # ===== ФОРМАТ 1: Читаемый для человека (сокращенный) =====
    readable_file = base_path / f"project_readable_{timestamp}.txt"

    with open(readable_file, 'w', encoding='utf-8') as f:
        f.write("=" * 80 + "\n")
        f.write(f"PROJECT SNAPSHOT (READABLE)\n")
        f.write(f"Created: {datetime.now()}\n")
        f.write(f"Project root: {base_path}\n")
        f.write("=" * 80 + "\n\n")

        # Структура папок
        f.write("FOLDER STRUCTURE:\n")
        f.write("-" * 40 + "\n")
        f.write(get_folder_structure(base_path, max_depth=4))

        # Список всех файлов с первой строкой
        f.write("\n\n" + "=" * 80 + "\n")
        f.write("ALL FILES (first line preview):\n")
        f.write("=" * 80 + "\n\n")

        all_files = collect_all_files(base_path)
        for file_path in sorted(all_files):
            rel_path = file_path.relative_to(base_path)
            try:
                with open(file_path, 'r', encoding='utf-8') as sf:
                    first_line = sf.readline().strip()
                    f.write(f"{rel_path} → {first_line[:100]}\n")
            except:
                f.write(f"{rel_path} → [BINARY OR ERROR]\n")

    # ===== ФОРМАТ 2: Полный для передачи (JSON) =====
    full_json = {
        "timestamp": datetime.now().isoformat(),
        "project_root": str(base_path),
        "files": {}
    }

    all_files = collect_all_files(base_path)
    for file_path in sorted(all_files):
        rel_path = str(file_path.relative_to(base_path)).replace('\\', '/')
        full_json["files"][rel_path] = get_file_content(file_path)

    json_file = base_path / f"project_full_{timestamp}.json"
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(full_json, f, indent=2, ensure_ascii=False)

    # ===== ФОРМАТ 3: ZIP-архив с полным кодом =====
    zip_file = base_path / f"project_code_{timestamp}.zip"
    with zipfile.ZipFile(zip_file, 'w', zipfile.ZIP_DEFLATED) as zf:
        for file_path in all_files:
            rel_path = str(file_path.relative_to(base_path))
            zf.write(file_path, rel_path)

    # ===== ИТОГ =====
    print("\n" + "=" * 60)
    print("✅ SNAPSHOTS CREATED")
    print("=" * 60)
    print(f"\n📄 Readable format (для быстрого просмотра):")
    print(f"   {readable_file.name}")
    print(f"   Размер: {readable_file.stat().st_size} байт")

    print(f"\n📦 JSON format (полный, для передачи):")
    print(f"   {json_file.name}")
    print(f"   Размер: {json_file.stat().st_size} байт")

    print(f"\n🗜️ ZIP archive (весь код):")
    print(f"   {zip_file.name}")
    print(f"   Размер: {zip_file.stat().st_size} байт")

    return json_file


if __name__ == "__main__":
    json_file = create_snapshot()
    print(f"\n📤 Отправь мне файл: {json_file.name}")