import os
import json
from pathlib import Path
from datetime import datetime


def generate_readme(output_file="README.md"):
    """Генерирует README на основе структуры проекта"""

    md_lines = []

    # Заголовок
    md_lines.append("# 🤖 AI Office")
    md_lines.append("")
    md_lines.append(
        "*Multi-agent AI system for automated code generation with clarifier, planner, developer and reviewer agents*\n")

    # Бейджи
    md_lines.append("[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)]()")
    md_lines.append("[![CrewAI](https://img.shields.io/badge/CrewAI-1.9.3-orange.svg)]()")
    md_lines.append("[![Streamlit](https://img.shields.io/badge/Streamlit-1.54.0-red.svg)]()")
    md_lines.append("[![Ollama](https://img.shields.io/badge/Ollama-phi3:mini-green.svg)]()")
    md_lines.append("[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)]()")
    md_lines.append("")

    # Описание
    md_lines.append("## 🎯 О проекте")
    md_lines.append("")
    md_lines.append(
        "**AI Office** — это multi-agent система для автоматической генерации кода на основе текстовых описаний. Проект использует локальные LLM (через Ollama) и агентный подход с разделением ролей для создания качественных веб-страниц и других проектов.\n")

    # Возможности
    md_lines.append("## ✨ Возможности")
    md_lines.append("")
    features = [
        "🤔 **Clarifier Agent** — задает уточняющие вопросы, если запрос неполный",
        "📐 **Planner Agent** — выбирает оптимальные технологии (HTML/CSS, Canvas, React)",
        "💻 **Developer Agent** — генерирует чистый, рабочий код",
        "🔍 **Reviewer Agent** — проверяет код на ошибки и соответствие требованиям",
        "📚 **Knowledge Base** — база знаний с примерами и best practices",
        "📊 **State Management** — структурированное хранение требований в JSON",
        "🖥️ **Streamlit UI** — удобный интерфейс с прогресс-барами",
        "📝 **Полное логирование** — все сессии сохраняются для анализа"
    ]
    for f in features:
        md_lines.append(f"- {f}")
    md_lines.append("")

    # Архитектура
    md_lines.append("## 🏗️ Архитектура")
    md_lines.append("")
    md_lines.append("```")
    md_lines.append("User Request → Clarifier → Parser → Planner → Knowledge Search → Developer → Reviewer → Output")
    md_lines.append("     ↑           ↓          ↓         ↓              ↓               ↓           ↓         ↓")
    md_lines.append("     └───────────┴─Questions┴─State──┴─────Examples────┴───────Code────┴─Feedback─┴───HTML")
    md_lines.append("```")
    md_lines.append("")

    # Компоненты
    components = [
        ("**Clarifier Agent**", "Анализирует запрос, задает уточняющие вопросы", "`agents/clarifier.py`"),
        ("**Parser**", "Преобразует запрос в структурированное состояние", "`core/state.py`"),
        ("**Planner Agent**", "Выбирает технологии на основе сложности", "`agents/planner.py`"),
        ("**Knowledge Search**", "Ищет примеры в базе знаний", "`core/knowledge_search.py`"),
        ("**Developer Agent**", "Генерирует HTML/CSS/JS код", "`agents/developer.py`"),
        ("**Reviewer Agent**", "Проверяет код на ошибки", "`agents/reviewer.py`"),
    ]

    for name, role, file in components:
        md_lines.append(f"- {name} — {role} ({file})")
    md_lines.append("")

    # Технологии
    md_lines.append("## 🛠️ Технологический стек")
    md_lines.append("")
    tech = [
        "**Python 3.10+** — основной язык",
        "**CrewAI 1.9.3** — фреймворк для multi-agent систем",
        "**Ollama** — запуск локальных LLM (phi3:mini, tinyllama)",
        "**Streamlit 1.54.0** — веб-интерфейс",
        "**phi3:mini** — основная модель (рекомендуется)",
        "**tinyllama** — альтернатива для слабых машин",
        "**SQLite** — хранение диалогов и проектов"
    ]
    for t in tech:
        md_lines.append(f"- {t}")
    md_lines.append("")

    # Установка
    md_lines.append("## 📦 Установка")
    md_lines.append("")
    install_steps = [
        ("1. **Клонировать репозиторий**",
         "git clone https://github.com/yourusername/ai-office.git\ncd ai-office"),
        ("2. **Создать виртуальное окружение**",
         "# Windows\nvenv\\Scripts\\activate\n# Linux/Mac\nsource venv/bin/activate"),
        ("3. **Установить зависимости**",
         "pip install -r requirements.txt"),
        ("4. **Установить и запустить Ollama**",
         "ollama pull phi3:mini\nollama serve"),
        ("5. **Запустить AI Office**",
         "# Консольный тест\npython test_full_pipeline.py\n\n# Веб-интерфейс\nstreamlit run ui/app.py")
    ]

    for desc, code in install_steps:
        md_lines.append(f"**{desc}**")
        md_lines.append("```bash")
        md_lines.append(code)
        md_lines.append("```")
        md_lines.append("")

    # Структура проекта
    md_lines.append("## 📁 Структура проекта")
    md_lines.append("")
    md_lines.append("```")
    md_lines.append("📦 ai-office")
    md_lines.append("├── 📂 agents/                 # Агенты системы")
    md_lines.append("│   ├── clarifier.py          # Уточнение требований")
    md_lines.append("│   ├── planner.py            # Выбор технологий")
    md_lines.append("│   ├── developer.py          # Генерация кода")
    md_lines.append("│   └── reviewer.py           # Проверка кода")
    md_lines.append("├── 📂 core/                   # Ядро системы")
    md_lines.append("│   ├── crew_runner.py        # Оркестрация агентов")
    md_lines.append("│   ├── state.py              # Состояние проекта")
    md_lines.append("│   ├── knowledge_search.py   # Поиск по базе знаний")
    md_lines.append("│   └── clarifier_loop.py     # Цикл уточнения")
    md_lines.append("├── 📂 knowledge_base/         # База знаний")
    md_lines.append("│   ├── cyberpunk_examples/   # Примеры киберпанк-лендингов")
    md_lines.append("│   ├── canvas/               # Canvas анимации")
    md_lines.append("│   ├── html/                 # HTML шаблоны")
    md_lines.append("│   ├── best_practices/       # Правила и рекомендации")
    md_lines.append("│   └── index.json            # Индекс примеров")
    md_lines.append("├── 📂 ui/                     # Веб-интерфейс")
    md_lines.append("│   └── app.py                # Streamlit приложение")
    md_lines.append("├── 📂 workspace/              # Результаты работы")
    md_lines.append("│   ├── temp/                 # Временные файлы")
    md_lines.append("│   └── projects/             # Сохраненные проекты")
    md_lines.append("├── test_full_pipeline.py     # Полный тест пайплайна")
    md_lines.append("├── project_snapshot.py       # Создание снимка проекта")
    md_lines.append("└── requirements.txt          # Зависимости")
    md_lines.append("```")
    md_lines.append("")

    # База знаний
    md_lines.append("## 📚 База знаний")
    md_lines.append("")
    md_lines.append("База знаний хранит примеры кода и best practices для разных технологий.\n")
    md_lines.append("**Как добавить пример:**")
    md_lines.append("")
    md_lines.append("1. Создай папку в `knowledge_base/` с названием технологии")
    md_lines.append("2. Добавь файлы проекта (index.html, style.css, script.js)")
    md_lines.append("3. Добавь запись в `index.json`:")
    md_lines.append("```json")
    md_lines.append('{')
    md_lines.append('  "id": "example_id",')
    md_lines.append('  "name": "Example Name",')
    md_lines.append('  "path": "folder/index.html",')
    md_lines.append('  "tech": "html",')
    md_lines.append('  "complexity": "medium",')
    md_lines.append('  "keywords": ["keyword1", "keyword2"],')
    md_lines.append('  "description": "Описание примера"')
    md_lines.append('}')
    md_lines.append("```")
    md_lines.append("")

    # Использование
    md_lines.append("## 🚀 Использование")
    md_lines.append("")
    md_lines.append("### Консольный тест")
    md_lines.append("```bash")
    md_lines.append("python test_full_pipeline.py")
    md_lines.append("# Выберите запрос:")
    md_lines.append("# 1. Сделай красивую анимацию")
    md_lines.append("# 2. Черный фон с белой линией")
    md_lines.append("# 3. Черный фон и белая линия которая медленно растет")
    md_lines.append("# 4. Свой вариант")
    md_lines.append("```")
    md_lines.append("")
    md_lines.append("### Веб-интерфейс")
    md_lines.append("```bash")
    md_lines.append("streamlit run ui/app.py")
    md_lines.append("# Открыть http://localhost:8501")
    md_lines.append("```")
    md_lines.append("")
    md_lines.append("### Примеры запросов")
    md_lines.append("```")
    md_lines.append("\"Создай страницу с черным фоном и белой линией, которая медленно растет\"")
    md_lines.append("\"Сделай футуристический лендинг в стиле киберпанк с неоновыми эффектами\"")
    md_lines.append("\"Создай анимацию с пульсирующим кругом\"")
    md_lines.append("```")
    md_lines.append("")

    # Производительность
    md_lines.append("## ⚡ Производительность")
    md_lines.append("")
    md_lines.append("- **CPU:** AMD Ryzen 7 (8 ядер, 16 потоков)")
    md_lines.append("- **RAM:** ~2-4 GB для phi3:mini")
    md_lines.append("- **Время генерации:** 1-3 минуты для средней сложности")
    md_lines.append("- **Параллельные запросы:** до 4")
    md_lines.append("")
    md_lines.append("**Оптимизация через `start.bat`:**")
    md_lines.append("```bash")
    md_lines.append("start.bat")
    md_lines.append("```")
    md_lines.append("")

    # Roadmap
    md_lines.append("## 🗺️ Roadmap")
    md_lines.append("")
    md_lines.append("### 🔥 Фаза 1 — Усиление агентов")
    md_lines.append("- [x] Clarifier с динамическими вопросами")
    md_lines.append("- [x] Knowledge Base с поиском")
    md_lines.append("- [ ] Planner с архитектурным планом")
    md_lines.append("- [ ] Reviewer с feedback loop")
    md_lines.append("")
    md_lines.append("### ⚡ Фаза 2 — Масштабирование")
    md_lines.append("- [ ] Семантический поиск в knowledge_base")
    md_lines.append("- [ ] Поддержка многофайловых проектов")
    md_lines.append("- [ ] Генерация Python скриптов")
    md_lines.append("- [ ] Интеграция с React")
    md_lines.append("")
    md_lines.append("### 🧠 Фаза 3 — Умные агенты")
    md_lines.append("- [ ] Self-reflection агентов")
    md_lines.append("- [ ] Автоматическое улучшение на основе feedback")
    md_lines.append("- [ ] Планирование сложных проектов")
    md_lines.append("")

    # Решение проблем
    md_lines.append("## 🔧 Решение проблем")
    md_lines.append("")
    md_lines.append("**Ollama не запускается**")
    md_lines.append("```bash")
    md_lines.append("taskkill /F /IM ollama.exe")
    md_lines.append("ollama serve")
    md_lines.append("```")
    md_lines.append("")
    md_lines.append("**Агенты пишут инструкции вместо кода**")
    md_lines.append("Проверь модель в `core/crew_runner.py`:")
    md_lines.append("```python")
    md_lines.append("os.environ[\"OPENAI_MODEL_NAME\"] = \"phi3:mini\"  # или tinyllama")
    md_lines.append("```")
    md_lines.append("")
    md_lines.append("**Слишком долго генерирует**")
    md_lines.append("Запусти через `start.bat` для оптимизации или используй `tinyllama` вместо `phi3:mini`")
    md_lines.append("")

    # Лицензия и авторы
    md_lines.append("## 📄 Лицензия")
    md_lines.append("")
    md_lines.append("MIT License — свободное использование, модификация и распространение.")
    md_lines.append("")
    md_lines.append("## ✨ Авторы")
    md_lines.append("")
    md_lines.append("- **Александр** — архитектор и разработчик")
    md_lines.append("- **Senior AI Systems Architect** — архитектурное руководство")
    md_lines.append("")
    md_lines.append("---")
    md_lines.append("*Создано с помощью AI Office* 🤖")

    # Сохраняем
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(md_lines))

    print(f"✅ README.md создан: {output_file}")
    return output_file


if __name__ == "__main__":
    generate_readme()