import os
import shutil
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from crewai import Crew, Task, Process
import traceback
import re

# Добавляем пути
import sys

# Пути
ROOT = Path(__file__).resolve().parent.parent
BACKUP_PATH = Path("C:/Users/Aki/Desktop/Need/Need/MyProject_AI-office/Backup")
WORKSPACE_PATH = ROOT / "workspace"
PROJECTS_PATH = WORKSPACE_PATH / "projects"
TEMP_PATH = WORKSPACE_PATH / "temp"

from agents.translator import create_translator
from agents.planner import create_planner
from agents.developer import create_developer
from agents.reviewer import create_reviewer
from core.complexity import ComplexityAnalyzer

load_dotenv()

# Пути
WORKSPACE_PATH = ROOT / "workspace"
PROJECTS_PATH = WORKSPACE_PATH / "projects"
TEMP_PATH = WORKSPACE_PATH / "temp"

# Настройки
os.environ["OPENAI_API_KEY"] = "ollama"
os.environ["OPENAI_API_BASE"] = "http://localhost:11434/v1"
os.environ["OPENAI_MODEL_NAME"] = "tinyllama"


def log_step(message):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")


def save_result(result_text, task_temp_dir, task_timestamp):
    """Сохраняет результат в файлы"""

    # Извлекаем чистый HTML если нужно
    if "```html" in result_text:
        html_match = re.search(r'```html\n(.*?)```', result_text, re.DOTALL)
        if html_match:
            result_text = html_match.group(1)
    elif "```" in result_text:
        code_match = re.search(r'```\n(.*?)```', result_text, re.DOTALL)
        if code_match:
            result_text = code_match.group(1)

    # Сохраняем HTML
    html_file = task_temp_dir / "index.html"
    with open(html_file, 'w', encoding='utf-8') as f:
        f.write(result_text)

    # Копируем в projects
    project_dir = PROJECTS_PATH / f"PROJECT_{task_timestamp}"
    project_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(html_file, project_dir)

    return html_file, project_dir


def run_crew(user_task: str):
    """Запускает агентов в зависимости от сложности"""

    log_step("=" * 60)
    log_step("🚀 АНАЛИЗ ЗАДАЧИ")
    log_step("=" * 60)

    # Анализируем сложность
    complexity = ComplexityAnalyzer.analyze(user_task)
    log_step(f"📊 Сложность: {complexity.name} (уровень {complexity.level})")
    log_step(f"📋 Нужны агенты: {', '.join(complexity.required_agents)}")

    # Создаём папку
    task_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    task_temp_dir = TEMP_PATH / f"task_{task_timestamp}"
    task_temp_dir.mkdir(parents=True, exist_ok=True)

    # Отчет
    report_file = task_temp_dir / "execution_report.md"
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(f"# Отчет о выполнении\n\n")
        f.write(f"**Задача:** {user_task}\n")
        f.write(f"**Сложность:** {complexity.name} (уровень {complexity.level})\n")
        f.write(f"**Агенты:** {', '.join(complexity.required_agents)}\n\n")

    try:
        current_input = user_task
        agents_used = []

        # 1. ПЕРЕВОДЧИК (если нужен)
        if "translator" in complexity.required_agents:
            log_step("🔄 Запуск переводчика...")
            translator = create_translator()

            task = Task(
                description=f"Convert to requirements:\n{current_input}",
                agent=translator,
                expected_output="Requirements list",
            )

            crew = Crew(agents=[translator], tasks=[task], verbose=False)
            current_input = crew.kickoff()
            current_input = current_input.raw if hasattr(current_input, 'raw') else str(current_input)
            agents_used.append("translator")

            with open(report_file, 'a', encoding='utf-8') as f:
                f.write(f"### 🔤 Переводчик\n\n{current_input}\n\n")

        # 2. ПЛАНИРОВЩИК (если нужен)
        if "planner" in complexity.required_agents:
            log_step("📋 Запуск планировщика...")
            planner = create_planner()

            task = Task(
                description=f"Create plan from:\n{current_input}",
                agent=planner,
                expected_output="Step-by-step plan",
            )

            crew = Crew(agents=[planner], tasks=[task], verbose=False)
            current_input = crew.kickoff()
            current_input = current_input.raw if hasattr(current_input, 'raw') else str(current_input)
            agents_used.append("planner")

            with open(report_file, 'a', encoding='utf-8') as f:
                f.write(f"### 📋 Планировщик\n\n{current_input}\n\n")

        # 3. РАЗРАБОТЧИК (всегда нужен)
        log_step("💻 Запуск разработчика...")
        developer = create_developer()

        task = Task(
            description=f"Write HTML code for:\n{current_input}\n\nOUTPUT ONLY HTML CODE",
            agent=developer,
            expected_output="<!DOCTYPE html>...",
        )

        crew = Crew(agents=[developer], tasks=[task], verbose=False)
        result = crew.kickoff()
        result_text = result.raw if hasattr(result, 'raw') else str(result)
        agents_used.append("developer")

        with open(report_file, 'a', encoding='utf-8') as f:
            f.write(f"### 💻 Разработчик\n\n```html\n{result_text}\n```\n\n")

        # 4. РЕВЬЮЕР (если нужен)
        if "reviewer" in complexity.required_agents:
            log_step("🔍 Запуск ревьюера...")
            reviewer = create_reviewer()

            task = Task(
                description=f"Review this code against requirements:\nCode:\n{result_text}\n\nRequirements:\n{current_input}",
                agent=reviewer,
                expected_output="APPROVE or REJECT",
            )

            crew = Crew(agents=[reviewer], tasks=[task], verbose=False)
            review = crew.kickoff()
            review_text = review.raw if hasattr(review, 'raw') else str(review)
            agents_used.append("reviewer")

            with open(report_file, 'a', encoding='utf-8') as f:
                f.write(f"### 🔍 Ревьюер\n\n{review_text}\n\n")

            if "REJECT" in review_text:
                log_step("❌ Код отклонен ревьюером")
                # Здесь можно добавить повторную попытку

        # Сохраняем результат
        html_file, project_dir = save_result(result_text, task_temp_dir, task_timestamp)

        with open(report_file, 'a', encoding='utf-8') as f:
            f.write(f"## ✅ Готово\n\n")
            f.write(f"**HTML:** {html_file}\n")
            f.write(f"**Проект:** {project_dir}\n")

        log_step(f"✅ HTML: {html_file}")
        log_step(f"✅ Проект: {project_dir}")

        return result_text

    except Exception as e:
        log_step(f"❌ Ошибка: {str(e)}")
        with open(report_file, 'a', encoding='utf-8') as f:
            f.write(f"\n## ❌ Ошибка\n\n```\n{traceback.format_exc()}\n```\n")
        raise e


if __name__ == "__main__":
    test_task = "Черный фон, белый текст"
    result = run_crew(test_task)
    print(result[:200])