import os
import shutil
import zipfile
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from crewai import Crew, Task, Process, Agent

load_dotenv()

# Пути
ROOT = Path(__file__).resolve().parent.parent
BACKUP_PATH = Path("C:/Users/Aki/Desktop/Need/Need/MyProject_AI-office/Backup")
WORKSPACE_PATH = ROOT / "workspace"
PROJECTS_PATH = WORKSPACE_PATH / "projects"
TEMP_PATH = WORKSPACE_PATH / "temp"

# Эти переменные уже должны быть в .env файле
os.environ["OPENAI_API_KEY"] = "ollama"
os.environ["OPENAI_API_BASE"] = "http://localhost:11434/v1"
os.environ["OPENAI_MODEL_NAME"] = "llama2"


def create_backup():
    """Создаёт бекап всех проектов и важных файлов"""
    try:
        # Создаём папку для бекапов, если её нет
        BACKUP_PATH.mkdir(parents=True, exist_ok=True)

        # Имя бекапа с датой и временем
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"backup_{timestamp}"
        backup_dir = BACKUP_PATH / backup_name
        backup_dir.mkdir(exist_ok=True)

        # 1. Бекап проектов
        if PROJECTS_PATH.exists():
            projects_backup = backup_dir / "projects"
            shutil.copytree(PROJECTS_PATH, projects_backup, dirs_exist_ok=True)

        # 2. Бекап временных файлов (если есть)
        if TEMP_PATH.exists():
            temp_backup = backup_dir / "temp"
            shutil.copytree(TEMP_PATH, temp_backup, dirs_exist_ok=True)

        # 3. Бекап конфигов
        config_files = ROOT.glob("*.env")
        if config_files:
            config_backup = backup_dir / "config"
            config_backup.mkdir(exist_ok=True)
            for env_file in config_files:
                shutil.copy2(env_file, config_backup / env_file.name)

        # 4. Создаём манифест бекапа
        manifest = backup_dir / "manifest.txt"
        with open(manifest, 'w') as f:
            f.write(f"Backup created: {datetime.now()}\n")
            f.write(f"Backup location: {backup_dir}\n")
            f.write("\n--- Project Files ---\n")

            if PROJECTS_PATH.exists():
                for item in PROJECTS_PATH.rglob("*"):
                    if item.is_file():
                        f.write(f"{item.relative_to(PROJECTS_PATH)}\n")

        # 5. Создаём архив для удобства
        zip_path = BACKUP_PATH / f"{backup_name}.zip"
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file in backup_dir.rglob("*"):
                if file.is_file() and file != zip_path:
                    zipf.write(file, file.relative_to(backup_dir))

        return {
            "success": True,
            "backup_dir": str(backup_dir),
            "backup_zip": str(zip_path),
            "timestamp": timestamp
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


def cleanup_temp_files(project_files=None):
    """Удаляет временные файлы"""
    if project_files is None:
        project_files = []

    # Удаляем временную директорию
    if TEMP_PATH.exists():
        try:
            shutil.rmtree(TEMP_PATH)
            print("🧹 Временные файлы очищены")
        except Exception as e:
            print(f"⚠️ Ошибка при очистке временных файлов: {e}")

    # Удаляем конкретные файлы проекта
    for file_path in project_files:
        try:
            if Path(file_path).exists():
                Path(file_path).unlink()
                print(f"🗑️ Удалён файл: {file_path}")
        except Exception as e:
            print(f"⚠️ Не удалось удалить {file_path}: {e}")


def create_agent(role, goal, backstory):
    """Создаёт агента с использованием переменных окружения"""
    return Agent(
        role=role,
        goal=goal,
        backstory=backstory,
        verbose=True,
        allow_delegation=False,
    )


def run_crew(user_task: str):
    """Запускает агентов с задачей"""

    # Создаём временную папку для проекта
    TEMP_PATH.mkdir(parents=True, exist_ok=True)

    # Создаём агентов
    planner = create_agent(
        "Planner",
        "Break down user tasks into clear steps. You are Ася - senior planner.",
        "You are a senior project planner named Ася."
    )

    developer = create_agent(
        "Developer",
        "Write clean working Python code. You are Джун-и - Python developer.",
        "You are an experienced Python developer named Джун-и."
    )

    reviewer = create_agent(
        "Reviewer",
        "Find bugs and improve code quality. You are Кай - strict code reviewer.",
        "You are a strict code reviewer named Кай."
    )

    # Задача 1: Планировщик
    plan_task = Task(
        description=f"""
        Проанализируй задачу пользователя и разбей её на чёткие шаги.
        Задача: {user_task}

        Твой ответ должен содержать:
        1. Понимание задачи
        2. Список конкретных шагов для разработчика
        3. Требования к коду
        """,
        agent=planner,
        expected_output="Детальный план реализации с пошаговыми инструкциями",
    )

    # Задача 2: Разработчик
    dev_task = Task(
        description="""
        Напиши чистый рабочий Python код на основе плана.

        План от планировщика:
        {plan_result}

        Требования:
        - Код должен быть готов к запуску
        - Добавь комментарии
        - Обработай возможные ошибки
        """,
        agent=developer,
        expected_output="Рабочий Python код с комментариями",
        context=[plan_task],
    )

    # Задача 3: Ревьюер
    review_task = Task(
        description="""
        Проверь код и найди проблемы.

        Код для проверки:
        {dev_result}

        Что проверить:
        1. Синтаксические ошибки
        2. Логические ошибки
        3. Стиль кода (PEP8)
        4. Предложения по улучшению

        Дай финальную версию кода с исправлениями.
        """,
        agent=reviewer,
        expected_output="Исправленный код с комментариями ревью",
        context=[dev_task],
    )

    crew = Crew(
        agents=[planner, developer, reviewer],
        tasks=[plan_task, dev_task, review_task],
        process=Process.sequential,
        verbose=True,
    )

    result = crew.kickoff()
    return result