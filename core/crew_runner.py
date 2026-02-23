import os
import shutil
import zipfile
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from crewai import Crew, Task, Process, Agent
import traceback
import time
import re

# Добавляем пути
import sys
ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT))

# Импорты наших модулей
from agents.translator import create_translator
from agents.planner import create_planner
from agents.developer import create_developer
from agents.reviewer import create_reviewer
from core.complexity import ComplexityAnalyzer
from core.requirements import ProjectRequirements

load_dotenv()

# Пути
ROOT = Path(__file__).resolve().parent.parent
BACKUP_PATH = Path("C:/Users/Aki/Desktop/Need/Need/MyProject_AI-office/Backup")
WORKSPACE_PATH = ROOT / "workspace"
PROJECTS_PATH = WORKSPACE_PATH / "projects"
TEMP_PATH = WORKSPACE_PATH / "temp"

# Оптимизированные настройки для Ryzen 7
os.environ["OPENAI_API_KEY"] = "ollama"
os.environ["OPENAI_API_BASE"] = "http://localhost:11434/v1"
os.environ["OPENAI_MODEL_NAME"] = "tinyllama"
os.environ["OPENAI_MAX_TOKENS"] = "2000"
os.environ["OPENAI_TEMPERATURE"] = "0.3"

# Кэш для агентов
_agent_cache = {}


def log_step(message):
    """Выводит шаг выполнения с временной меткой"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] {message}")


def auto_cleanup(max_age_hours: int = 24):
    """Автоматически удаляет старые временные файлы"""
    try:
        now = time.time()
        # Чистим temp папки старше max_age_hours
        if TEMP_PATH.exists():
            for item in TEMP_PATH.glob("task_*"):
                if item.is_dir():
                    age = now - item.stat().st_mtime
                    if age > max_age_hours * 3600:
                        shutil.rmtree(item, ignore_errors=True)
                        log_step(f"🧹 Удалена старая папка: {item.name}")

        # Чистим старые проекты (можно оставить, но с пометкой)
        if PROJECTS_PATH.exists():
            for item in PROJECTS_PATH.glob("project_*"):
                if item.is_dir():
                    age = now - item.stat().st_mtime
                    if age > max_age_hours * 24 * 7:  # Неделя
                        shutil.rmtree(item, ignore_errors=True)
                        log_step(f"🗑️ Удален старый проект: {item.name}")
    except Exception as e:
        log_step(f"⚠️ Ошибка при очистке: {e}")


def create_backup(async_mode=True):
    """Создаёт бекап асинхронно"""
    if async_mode:
        import threading
        thread = threading.Thread(target=_create_backup_sync)
        thread.daemon = True
        thread.start()
        log_step("🔄 Бекап запущен в фоне")
        return {"success": True, "async": True}
    else:
        return _create_backup_sync()


def _create_backup_sync():
    """Синхронное создание бекапа"""
    try:
        log_step("Создание бекапа...")
        BACKUP_PATH.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"backup_{timestamp}"
        backup_dir = BACKUP_PATH / backup_name
        backup_dir.mkdir(exist_ok=True)

        if PROJECTS_PATH.exists():
            projects_backup = backup_dir / "projects"
            shutil.copytree(PROJECTS_PATH, projects_backup, dirs_exist_ok=True)
            log_step(f"✅ Проекты сохранены")

        log_step(f"✅ Бекап завершён: {backup_name}")
        return {"success": True, "backup_dir": str(backup_dir), "timestamp": timestamp}
    except Exception as e:
        log_step(f"❌ Ошибка бекапа: {str(e)}")
        return {"success": False, "error": str(e)}


def cleanup_temp_files(project_files=None):
    """Быстрая очистка временных файлов"""
    if project_files is None:
        project_files = []

    if TEMP_PATH.exists():
        try:
            shutil.rmtree(TEMP_PATH, ignore_errors=True)
            log_step("🧹 Временные файлы очищены")
        except:
            pass


def create_agent(role, goal, backstory):
    """Создаёт агента с кэшированием"""
    cache_key = f"{role}_{goal[:50]}"

    if cache_key in _agent_cache:
        log_step(f"⚡ Агент {role} взят из кэша")
        return _agent_cache[cache_key]

    log_step(f"🤖 Создание агента: {role}")

    agent = Agent(
        role=role,
        goal=goal,
        backstory=backstory,
        verbose=False,
        allow_delegation=False,
        max_rpm=10,
        max_iter=3,
    )

    _agent_cache[cache_key] = agent
    return agent


def validate_result(result_text, task):
    """Проверяет, действительно ли агенты что-то сделали"""
    issues = []

    # Проверка 1: Длина результата
    if len(result_text) < 50:
        issues.append(f"❌ Результат слишком короткий ({len(result_text)} символов)")

    # Проверка 2: Есть ли реальный код
    if "def " not in result_text and "class " not in result_text and "```" not in result_text:
        issues.append("❌ В результате нет кода (нет def/class/```)")

    # Проверка 3: Есть ли HTML для сайта
    if "сайт" in task.lower() or "html" in task.lower() or "страниц" in task.lower():
        if "<html" not in result_text.lower() and "!doctype" not in result_text.lower():
            issues.append("❌ Для сайта нет HTML кода")

    # Проверка 4: Есть ли анимация
    if "анимац" in task.lower() or "движ" in task.lower():
        if "@keyframes" not in result_text and "animation" not in result_text:
            issues.append("❌ Нет анимации (нет @keyframes или animation)")

    # Проверка 5: Есть ли темная тема
    if "темн" in task.lower() or "dark" in task.lower():
        if "background-color: #" not in result_text and "background: #" not in result_text:
            issues.append("❌ Нет темного фона")

    return issues


def save_agent_outputs(planner_output, developer_output, reviewer_output, task, temp_dir):
    """Сохраняет результаты каждого агента"""
    timestamp = datetime.now().strftime("%H%M%S")

    # Сохраняем план
    if planner_output:
        plan_file = temp_dir / f"plan_{timestamp}.md"
        with open(plan_file, 'w', encoding='utf-8') as f:
            f.write("# План выполнения\n\n")
            f.write(f"**Задача:** {task}\n\n")
            f.write(str(planner_output))
        log_step(f"📋 План сохранен: {plan_file}")

    # Сохраняем код разработчика
    if developer_output:
        dev_file = temp_dir / f"developer_code_{timestamp}.py"
        with open(dev_file, 'w', encoding='utf-8') as f:
            f.write("# Код разработчика\n\n")
            f.write(f"# Задача: {task}\n\n")
            f.write(str(developer_output))
        log_step(f"💻 Код разработчика сохранен: {dev_file}")

    # Сохраняем ревью
    if reviewer_output:
        review_file = temp_dir / f"review_{timestamp}.md"
        with open(review_file, 'w', encoding='utf-8') as f:
            f.write("# Результат проверки\n\n")
            f.write(str(reviewer_output))
        log_step(f"🔍 Ревью сохранено: {review_file}")


def generate_project_name(user_task: str, requirements=None):
    """Генерирует имя проекта на основе задачи и требований"""
    try:
        if requirements and hasattr(requirements, 'generate_project_name'):
            return requirements.generate_project_name()

        # Пробуем извлечь из задачи
        words = user_task.split()[:3]
        # Очищаем от спецсимволов
        clean_words = []
        for w in words:
            # Убираем эмодзи и спецсимволы
            clean = ''.join(c for c in w if c.isalnum())
            if clean:
                clean_words.append(clean)

        if clean_words:
            base_name = '_'.join(clean_words)
            return base_name
    except:
        pass

    return "Project"


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

    # Создаём папку
    task_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    task_temp_dir = TEMP_PATH / f"task_{task_timestamp}"
    task_temp_dir.mkdir(parents=True, exist_ok=True)

    # Отчет
    report_file = task_temp_dir / "execution_report.md"
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(f"# Отчет о выполнении\n\n")
        f.write(f"**Задача:** {user_task}\n")
        f.write(f"**Начало:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

    try:
        # ===== ШАГ 0: ИСПОЛЬЗУЕМ LLM EXTRACTOR =====
        from core.llm_extractor import LLMExtractor
        extractor = LLMExtractor()

        log_step("🤖 Извлечение требований через LLM...")
        result = extractor.extract(user_task)

        # Проверяем тип результата
        if isinstance(result, str):
            log_step("⚠️ LLM вернул строку, пробую распарсить...")
            try:
                import json
                # Пробуем найти JSON в строке
                json_match = re.search(r'\{.*\}', result, re.DOTALL)
                if json_match:
                    requirements_dict = json.loads(json_match.group())
                else:
                    raise ValueError("No JSON found")
            except:
                log_step("❌ Не удалось распарсить JSON, создаю пустой словарь")
                requirements_dict = {
                    "project_type": None,
                    "technologies": [],
                    "forbidden": [],
                    "colors": [],
                    "style": None,
                    "animation_speed": None,
                    "features": [],
                    "mood": None,
                    "has_examples": False,
                    "confidence": 0.1,
                    "missing_info": ["LLM returned string instead of dict"]
                }
        else:
            requirements_dict = result

        # Преобразуем в текст для агентов
        requirements_text = ""
        if isinstance(requirements_dict, dict):
            for key, value in requirements_dict.items():
                if value and key not in ['confidence', 'missing_info']:
                    if isinstance(value, list):
                        if value:
                            requirements_text += f"- {key}: {', '.join(value)}\n"
                    else:
                        requirements_text += f"- {key}: {value}\n"
        else:
            requirements_text = str(requirements_dict)
            log_step("⚠️ requirements_dict не является словарем")

        log_step(f"📋 Извлеченные требования:\n{requirements_text}")

        with open(report_file, 'a', encoding='utf-8') as f:
            f.write(f"### 🔤 Извлечение требований (LLM)\n\n")
            f.write(f"```\n{requirements_text}\n```\n\n")

        # Анализируем сложность
        complexity = ComplexityAnalyzer.analyze(requirements_dict)
        log_step(f"📊 Сложность: {complexity.name} (уровень {complexity.level})")
        log_step(f"📋 Нужны агенты: {', '.join(complexity.required_agents)}")

        current_input = requirements_text  # Теперь используем структурированные требования

        # 1. ПЕРЕВОДЧИК (если нужен)
        if "translator" in complexity.required_agents:
            log_step("🔄 Запуск переводчика...")
            translator = create_translator()

            task = Task(
                description=f"Convert these requirements into clear technical specs:\n{current_input}",
                agent=translator,
                expected_output="Technical specifications",
            )

            crew = Crew(agents=[translator], tasks=[task], verbose=False)
            current_input = crew.kickoff()
            current_input = current_input.raw if hasattr(current_input, 'raw') else str(current_input)

            with open(report_file, 'a', encoding='utf-8') as f:
                f.write(f"### 🔤 Переводчик\n\n{current_input}\n\n")

        # 2. ПЛАНИРОВЩИК (если нужен)
        if "planner" in complexity.required_agents:
            log_step("📋 Запуск планировщика...")
            planner = create_planner()

            task = Task(
                description=f"Create detailed technical plan from:\n{current_input}",
                agent=planner,
                expected_output="Step-by-step technical plan",
            )

            crew = Crew(agents=[planner], tasks=[task], verbose=False)
            current_input = crew.kickoff()
            current_input = current_input.raw if hasattr(current_input, 'raw') else str(current_input)

            with open(report_file, 'a', encoding='utf-8') as f:
                f.write(f"### 📋 Планировщик\n\n{current_input}\n\n")

        # 3. РАЗРАБОТЧИК (всегда нужен)
        log_step("💻 Запуск разработчика...")
        developer = create_developer()

        # Вместо жесткой строки:
        task = Task(
            description=f"""Write HTML code based on these requirements and plan:

        REQUIREMENTS:
        {requirements_text}

        PLAN:
        {current_input if 'planner' in complexity.required_agents else 'Use best practices'}

        CRITICAL RULES:
        - Start with <!DOCTYPE html>
        - End with </html>
        - NO explanations before or after code
        - JUST THE HTML CODE

        OUTPUT ONLY THE CODE:""",
            agent=developer,
            expected_output="<!DOCTYPE html>...",
        )

        crew = Crew(
            agents=[developer],
            tasks=[task],
            verbose=False,
            cache=False  # <-- ОТКЛЮЧАЕМ КЭШ
        )
        result = crew.kickoff()
        result_text = result.raw if hasattr(result, 'raw') else str(result)

        with open(report_file, 'a', encoding='utf-8') as f:
            f.write(f"### 💻 Разработчик\n\n```html\n{result_text}\n```\n\n")

        # 4. РЕВЬЮЕР (если нужен)
        if "reviewer" in complexity.required_agents:
            log_step("🔍 Запуск ревьюера...")
            reviewer = create_reviewer()

            task = Task(
                description=f"""Review this HTML code against requirements:

REQUIREMENTS:
{requirements_text}

CODE:
{result_text}

Check:
1. Does it meet the requirements?
2. Is the code valid?
3. Are there any naive implementations?

If approved, say "APPROVE"
If rejected, say "REJECT: reason" and suggest improvements""",
                agent=reviewer,
                expected_output="APPROVE or REJECT with reason",
            )

            crew = Crew(agents=[reviewer], tasks=[task], verbose=False)
            review = crew.kickoff()
            review_text = review.raw if hasattr(review, 'raw') else str(review)

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
    print("=" * 50)
    print("ТЕСТОВЫЙ ЗАПУСК")
    print("=" * 50)
    test_task = "Создай простую HTML страницу с заголовком"
    result = run_crew(test_task)
    print(f"Результат: {result}")