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


def run_crew(user_task: str):
    """Запускает агентов с задачей и принудительной проверкой результатов"""
    log_step(f"📥 Получена задача: {user_task[:100]}...")

    # Создаём временную папку с уникальным именем
    task_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    task_temp_dir = TEMP_PATH / f"task_{task_timestamp}"
    task_temp_dir.mkdir(parents=True, exist_ok=True)
    log_step(f"📂 Рабочая папка: {task_temp_dir}")

    # Создаем отчет о выполнении
    report_file = task_temp_dir / "execution_report.md"
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(f"# Отчет о выполнении задачи\n\n")
        f.write(f"**Задача:** {user_task}\n")
        f.write(f"**Начало:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write("## Этапы выполнения\n\n")

    try:
        # Создаём агентов
        planner = create_agent(
            "Planner",
            "Create detailed technical plan. Must include specific steps and requirements.",
            "You are Ася - senior technical planner. Always provide detailed plans."
        )

        developer = create_agent(
            "Developer",
            "Write complete, working code. Include all necessary HTML, CSS, JavaScript.",
            "You are Джун-и - full-stack developer. Always provide runnable code."
        )

        reviewer = create_agent(
            "Reviewer",
            "Check code thoroughly. Verify it works and meets requirements.",
            "You are Кай - strict code reviewer. Never approve incomplete code."
        )

        # Новый агент - Переводчик
        translator = create_agent(
            "Translator",
            """You are a prompt engineer. Your ONLY task is to convert user requests into EXACT technical specifications.

            Rules:
            1. Remove all natural language, keep only technical requirements
            2. Specify EXACT output format (HTML, CSS, JS)
            3. Forbid frameworks and libraries
            4. Require single file output
            5. Demand specific features

            Example input: "Сделай красивый сайт с анимацией"
            Example output: "Create ONE HTML file with: CSS animations, dark theme, grayscale effect. NO frameworks, NO external libraries. All code in one file."
            """,
            "You are a strict technical translator. You convert vague requests into precise specifications."
        )

        # Задача переводчика
        translate_task = Task(
            description=f"""
            Convert this user request into EXACT technical specifications:

            {user_task}

            Your response MUST be ONLY the technical spec. No explanations, no comments.
            The spec must specify: file format, required features, forbidden elements.
            """,
            agent=translator,
            expected_output="Technical specification with exact requirements",
        )

        with open(report_file, 'a', encoding='utf-8') as f:
            f.write(f"### 🔤 Переводчик\n\n")
            f.write(f"**Начало:** {datetime.now().strftime('%H:%M:%S')}\n\n")

        # === ШАГ 1: ПЕРЕВОДЧИК ===
        log_step("🔄 Запуск переводчика...")
        translate_crew = Crew(
            agents=[translator],
            tasks=[translate_task],
            verbose=False
        )
        translate_result = translate_crew.kickoff()
        log_step(f"📝 Техническое задание: {str(translate_result)[:100]}...")

        with open(report_file, 'a', encoding='utf-8') as f:
            f.write(f"**Результат:**\n```\n{translate_result}\n```\n\n")
            f.write(f"**Завершение:** {datetime.now().strftime('%H:%M:%S')}\n\n")
            f.write("---\n\n")
            f.write(f"### 📋 Планировщик (Ася)\n\n")
            f.write(f"**Начало:** {datetime.now().strftime('%H:%M:%S')}\n\n")

        # === ШАГ 2: ПЛАНИРОВЩИК (с техзаданием от переводчика) ===
        log_step("📋 Запуск планировщика...")
        plan_task = Task(
            description=f"""
            Create a DETAILED TECHNICAL PLAN based on this specification:

            {translate_result}

            Your plan MUST include:
            1. EXACT HTML structure
            2. Specific CSS animations with @keyframes
            3. JavaScript functionality
            4. Color scheme (dark theme)

            The plan should be IMPLEMENTATION-READY.
            """,
            agent=planner,
            expected_output="Detailed technical plan with specific code structure",
        )

        planner_crew = Crew(
            agents=[planner],
            tasks=[plan_task],
            verbose=False
        )
        planner_result = planner_crew.kickoff()

        with open(report_file, 'a', encoding='utf-8') as f:
            f.write(f"**Результат:**\n```\n{planner_result}\n```\n\n")
            f.write(f"**Завершение:** {datetime.now().strftime('%H:%M:%S')}\n\n")
            f.write("---\n\n")
            f.write(f"### 💻 Разработчик (Джун-и)\n\n")
            f.write(f"**Начало:** {datetime.now().strftime('%H:%M:%S')}\n\n")

        # === ШАГ 3: РАЗРАБОТЧИК ===
        log_step("💻 Запуск разработчика...")
        dev_task = Task(
            description=f"""
            WRITE COMPLETE HTML CODE based on this plan.

            Plan:
            {planner_result}

            CRITICAL REQUIREMENTS:
            - Output MUST be ONLY the HTML code
            - Start with <!DOCTYPE html>
            - Include <style> for CSS animations
            - Include <script> for any JavaScript
            - DARK THEME (dark backgrounds)
            - ABSTRACT ANIMATION (moving pattern)
            - NO explanations, NO comments about the code
            - JUST THE CODE, nothing else

            The code must work when saved as .html and opened in browser.
            """,
            agent=developer,
            expected_output="Complete HTML code with CSS and JavaScript",
            timeout=180,
        )

        dev_crew = Crew(
            agents=[developer],
            tasks=[dev_task],
            verbose=False
        )
        developer_result = dev_crew.kickoff()

        # Проверяем, что разработчик выдал код, а не текст
        dev_result_str = str(developer_result)
        if "<!DOCTYPE" not in dev_result_str and "<html" not in dev_result_str:
            log_step("⚠️ Разработчик не выдал HTML, пробую еще раз с жестким промптом...")

            # Повторный запрос с еще более жесткими требованиями
            dev_task_retry = Task(
                description=f"""
                YOU MUST OUTPUT ONLY HTML CODE. NO TEXT. NO EXPLANATIONS.

                START YOUR RESPONSE WITH: <!DOCTYPE html>

                Create a dark-themed page with moving abstract pattern.

                REQUIRED ELEMENTS:
                - Dark background (black or dark gray)
                - Animated pattern using CSS @keyframes
                - JavaScript for grayscale effect

                YOUR ENTIRE RESPONSE MUST BE THE HTML CODE.
                DO NOT EXPLAIN WHAT YOU DID.
                DO NOT DESCRIBE THE CODE.
                JUST OUTPUT THE CODE.
                """,
                agent=developer,
                expected_output="<!DOCTYPE html> ... </html>",
                timeout=120,
            )

            dev_crew_retry = Crew(
                agents=[developer],
                tasks=[dev_task_retry],
                verbose=False
            )
            developer_result = dev_crew_retry.kickoff()

        with open(report_file, 'a', encoding='utf-8') as f:
            f.write(f"**Результат:**\n```html\n{developer_result}\n```\n\n")
            f.write(f"**Завершение:** {datetime.now().strftime('%H:%M:%S')}\n\n")
            f.write("---\n\n")
            f.write(f"### 🔍 Ревьюер (Кай)\n\n")
            f.write(f"**Начало:** {datetime.now().strftime('%H:%M:%S')}\n\n")

        # === ШАГ 4: РЕВЬЮЕР ===
        log_step("🔍 Запуск ревьюера...")
        review_task = Task(
            description=f"""
            REVIEW this HTML code:

            {developer_result}

            CHECK:
            1. Does it start with <!DOCTYPE>?
            2. Does it have dark background?
            3. Does it have CSS animation (@keyframes)?
            4. Does it have grayscale effect?

            If ANY requirement is missing, FIX THE CODE.

            OUTPUT THE FINAL, WORKING HTML CODE ONLY.
            NO EXPLANATIONS. JUST THE CODE.
            """,
            agent=reviewer,
            expected_output="Fixed and working HTML code",
            timeout=120,
        )

        review_crew = Crew(
            agents=[reviewer],
            tasks=[review_task],
            verbose=False
        )
        reviewer_result = review_crew.kickoff()

        with open(report_file, 'a', encoding='utf-8') as f:
            f.write(f"**Результат:**\n```html\n{reviewer_result}\n```\n\n")
            f.write(f"**Завершение:** {datetime.now().strftime('%H:%M:%S')}\n\n")

        # Сохраняем результаты всех агентов
        save_agent_outputs(planner_result, developer_result, reviewer_result, user_task, task_temp_dir)

        # Берем финальный результат (от ревьюера)
        final_result = reviewer_result

        # Проверяем результат
        result_text = str(final_result)
        issues = validate_result(result_text, user_task)

        with open(report_file, 'a', encoding='utf-8') as f:
            f.write("## ✅ Итоговая проверка\n\n")
            if issues:
                f.write("### ❌ Найденные проблемы:\n\n")
                for issue in issues:
                    f.write(f"- {issue}\n")
                f.write("\n⚠️ Требуется доработка!\n")
                log_step("⚠️ Обнаружены проблемы в результате:")
                for issue in issues:
                    log_step(f"  {issue}")
            else:
                f.write("✅ Все проверки пройдены! Код готов.\n")
                log_step("✅ Все проверки пройдены!")

        # Сохраняем финальный результат в разных форматах
        html_file = task_temp_dir / "index.html"
        with open(html_file, 'w', encoding='utf-8') as f:
            # Извлекаем HTML если он есть в markdown
            html_content = result_text
            if "```html" in result_text:
                html_content = re.findall(r'```html\n(.*?)```', result_text, re.DOTALL)
                if html_content:
                    html_content = html_content[0]
            elif "```" in result_text:
                code_blocks = re.findall(r'```\n(.*?)```', result_text, re.DOTALL)
                if code_blocks:
                    html_content = code_blocks[0]

            f.write(html_content)

        log_step(f"✅ HTML файл сохранен: {html_file}")
        log_step(f"✅ Отчет сохранен: {report_file}")

        # Если есть HTML, создаем превью
        if html_file.exists():
            preview_file = task_temp_dir / "preview.html"
            with open(preview_file, 'w', encoding='utf-8') as f:
                f.write("""<!DOCTYPE html>
<html>
<head>
    <title>Preview</title>
    <style>
        body { margin: 0; padding: 20px; background: #1a1a1a; color: #fff; }
        iframe { width: 100%; height: 80vh; border: 1px solid #333; border-radius: 8px; }
    </style>
</head>
<body>
    <h2>Preview generated code:</h2>
    <iframe srcdoc='""")

                # Экранируем содержимое для iframe
                with open(html_file, 'r', encoding='utf-8') as src:
                    content = src.read().replace("'", "\\'").replace("\n", " ")
                    f.write(content)

                f.write("'></iframe>\n</body>\n</html>")

            log_step(f"👁️ Превью доступно: {preview_file}")

        # Копируем в общую папку projects
        project_name = f"project_{task_timestamp}"
        project_dir = PROJECTS_PATH / project_name
        project_dir.mkdir(parents=True, exist_ok=True)

        for file in task_temp_dir.glob("*"):
            shutil.copy2(file, project_dir)

        log_step(f"📁 Проект сохранен: {project_dir}")

        return final_result

    except Exception as e:
        log_step(f"❌ КРИТИЧЕСКАЯ ОШИБКА: {str(e)}")
        log_step(f"📝 Детали: {traceback.format_exc()}")

        # Сохраняем ошибку в отчет
        with open(report_file, 'a', encoding='utf-8') as f:
            f.write(f"\n## ❌ ОШИБКА\n\n")
            f.write(f"```\n{traceback.format_exc()}\n```\n")

        raise e


if __name__ == "__main__":
    print("=" * 50)
    print("ТЕСТОВЫЙ ЗАПУСК")
    print("=" * 50)
    test_task = "Создай простую HTML страницу с заголовком"
    result = run_crew(test_task)
    print(f"Результат: {result}")