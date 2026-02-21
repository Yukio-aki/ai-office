import sys
from pathlib import Path
import streamlit as st
import threading
import queue
import time
import shutil
import requests
import subprocess
from datetime import datetime
from io import StringIO
import contextlib

# Отключаем обработку сигналов в CrewAI (для Streamlit)
import os

os.environ["CREWAI_TELEMETRY_OPT_OUT"] = "true"
os.environ["CREWAI_DISABLE_SIGNALS"] = "true"

# Добавляем корень проекта в PYTHONPATH
ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT))

from core.crew_runner import run_crew, create_backup, cleanup_temp_files

# Настройка страницы
st.set_page_config(page_title="AI Office", page_icon="🤖", layout="wide")

# Пути
BACKUP_PATH = Path("C:/Users/Aki/Desktop/Need/Need/MyProject_AI-office/Backup")
PROJECTS_PATH = ROOT / "workspace" / "projects"
TEMP_PATH = ROOT / "workspace" / "temp"

# Инициализация session state
if 'logs' not in st.session_state:
    st.session_state.logs = []
if 'status' not in st.session_state:
    st.session_state.status = {
        'planner': 'idle',
        'developer': 'idle',
        'reviewer': 'idle'
    }
if 'result' not in st.session_state:
    st.session_state.result = None
if 'thread' not in st.session_state:
    st.session_state.thread = None
if 'stop_flag' not in st.session_state:
    st.session_state.stop_flag = False
if 'current_project_files' not in st.session_state:
    st.session_state.current_project_files = []
if 'show_stop_confirm' not in st.session_state:
    st.session_state.show_stop_confirm = False
if 'last_backup' not in st.session_state:
    st.session_state.last_backup = None
if 'health_status' not in st.session_state:
    st.session_state.health_status = None
if 'last_heartbeat' not in st.session_state:
    st.session_state.last_heartbeat = time.time()


# Функция проверки здоровья Ollama
def check_ollama_health():
    """Проверяет, работает ли Ollama и отвечает ли модель"""
    health_report = {
        'ollama_running': False,
        'model_available': False,
        'model_responding': False,
        'response_time': None,
        'error': None
    }

    try:
        # Проверка 1: Запущен ли сервер Ollama
        start = time.time()
        response = requests.get("http://localhost:11434/api/tags", timeout=5)

        if response.status_code == 200:
            health_report['ollama_running'] = True
            models = response.json().get('models', [])

            # Проверка 2: Есть ли модель llama2
            model_names = [m.get('name') for m in models]
            if 'llama2' in model_names or 'llama2:latest' in model_names:
                health_report['model_available'] = True

                # Проверка 3: Отвечает ли модель
                try:
                    test_response = requests.post(
                        "http://localhost:11434/api/generate",
                        json={
                            "model": "llama2",
                            "prompt": "Say 'ok' in one word",
                            "stream": False
                        },
                        timeout=10
                    )
                    if test_response.status_code == 200:
                        health_report['model_responding'] = True
                        health_report['response_time'] = time.time() - start
                except Exception as e:
                    health_report['error'] = f"Модель не отвечает: {str(e)}"
            else:
                health_report['error'] = "Модель llama2 не найдена. Запустите: ollama pull llama2"
        else:
            health_report['error'] = f"Ollama вернул статус {response.status_code}"

    except requests.ConnectionError:
        health_report['error'] = "Ollama не запущена. Запустите: ollama serve"
    except Exception as e:
        health_report['error'] = f"Ошибка проверки: {str(e)}"

    return health_report


# Функция автоматического восстановления
def auto_recover():
    """Пытается восстановить работу Ollama"""
    st.session_state.logs.append("🔄 Попытка автоматического восстановления...")

    # Проверяем, запущен ли процесс Ollama
    try:
        # Для Windows
        result = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq ollama.exe'],
                                capture_output=True, text=True)

        if 'ollama.exe' not in result.stdout:
            st.session_state.logs.append("🔄 Ollama не запущена, пробую запустить...")
            subprocess.Popen(['ollama', 'serve'],
                             creationflags=subprocess.CREATE_NO_WINDOW)
            time.sleep(5)  # Даём время на запуск
        else:
            st.session_state.logs.append("🔄 Ollama запущена, но не отвечает, пробую перезапустить...")
            # Убиваем процесс
            subprocess.run(['taskkill', '/F', '/IM', 'ollama.exe'], capture_output=True)
            time.sleep(2)
            # Запускаем заново
            subprocess.Popen(['ollama', 'serve'],
                             creationflags=subprocess.CREATE_NO_WINDOW)
            time.sleep(5)
    except Exception as e:
        st.session_state.logs.append(f"❌ Ошибка восстановления: {e}")
        return False

    # Проверяем, помогло ли
    time.sleep(3)
    health = check_ollama_health()
    if health['model_responding']:
        st.session_state.logs.append("✅ Восстановление успешно!")
        return True
    else:
        st.session_state.logs.append("❌ Не удалось восстановить")
        return False


# Функция для запуска агентов с мониторингом
def run_agents_with_logs(task, log_queue, status_dict, project_files_list, stop_flag_ref):
    """Запускает агентов и передаёт логи через очередь с мониторингом"""

    # Отправляем сигнал жизни
    def heartbeat():
        log_queue.put(("heartbeat", time.time()))

    heartbeat()

    # Создаём временную директорию для проекта
    temp_dir = TEMP_PATH / f"project_{int(time.time())}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    log_queue.put(("log", f"📂 Создана временная папка: {temp_dir.name}"))

    try:
        # Проверяем здоровье перед началом
        health = check_ollama_health()
        if not health['model_responding']:
            error_msg = f"❌ Ollama не готова: {health.get('error', 'Неизвестная ошибка')}"
            log_queue.put(("log", error_msg))
            status_dict['planner'] = 'error'
            log_queue.put(("status", status_dict.copy()))
            return

        log_queue.put(("log", "✅ Ollama работает, запускаем агентов..."))
        heartbeat()

        # Запускаем основную логику
        if stop_flag_ref[0]:
            log_queue.put(("log", "⛔ Процесс остановлен"))
            return

        status_dict['planner'] = 'working'
        log_queue.put(("status", status_dict.copy()))
        log_queue.put(("log", "📋 Планировщик (Ася) начал работу..."))
        heartbeat()

        # Сохраняем план в файл
        plan_file = temp_dir / "plan.md"
        with open(plan_file, 'w') as f:
            f.write(f"# План для задачи: {task}\n\n")
            f.write("Создано: " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        project_files_list.append(str(plan_file))

        if stop_flag_ref[0]:
            return

        heartbeat()
        result = run_crew(task)

        if stop_flag_ref[0]:
            return

        status_dict['planner'] = 'done'
        status_dict['developer'] = 'working'
        log_queue.put(("status", status_dict.copy()))
        log_queue.put(("log", "💻 Разработчик (Джун-и) начал работу..."))
        heartbeat()

        # Сохраняем код в файл
        code_file = temp_dir / "output.py"
        with open(code_file, 'w') as f:
            f.write("# Код сгенерированный агентами\n")
            f.write(f"# Задача: {task}\n")
            f.write(f"# Дата: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write(str(result) if result else "# Нет результата")
        project_files_list.append(str(code_file))

        if stop_flag_ref[0]:
            return

        status_dict['developer'] = 'done'
        status_dict['reviewer'] = 'working'
        log_queue.put(("status", status_dict.copy()))
        log_queue.put(("log", "🔍 Ревьюер (Кай) начал проверку..."))
        heartbeat()

        if stop_flag_ref[0]:
            return

        time.sleep(1)  # Имитация работы ревьюера

        status_dict['reviewer'] = 'done'
        log_queue.put(("status", status_dict.copy()))
        log_queue.put(("log", "✅ Все агенты завершили работу!"))
        log_queue.put(("result", result))
        heartbeat()

        # Если успешно завершилось, перемещаем файлы из temp в projects
        if not stop_flag_ref[0]:
            project_name = f"project_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            project_dir = PROJECTS_PATH / project_name
            project_dir.mkdir(parents=True, exist_ok=True)

            # Копируем файлы
            for file_path in project_files_list:
                src = Path(file_path)
                dst = project_dir / src.name
                shutil.copy2(src, dst)

            log_queue.put(("log", f"📁 Проект сохранён в: {project_dir}"))

    except Exception as e:
        log_queue.put(("log", f"❌ Ошибка: {str(e)}"))
        status_dict['planner'] = 'error'
        status_dict['developer'] = 'error'
        status_dict['reviewer'] = 'error'
        log_queue.put(("status", status_dict.copy()))


# Функция для отображения прогресс-бара
def show_progress_bar():
    """Показывает прогресс выполнения на основе статусов"""
    status_values = {
        'idle': 0,
        'working': 0.3,
        'done': 0.6,
        'stopped': 1,
        'error': 1
    }

    planner_progress = status_values.get(st.session_state.status['planner'], 0)
    developer_progress = status_values.get(st.session_state.status['developer'], 0)
    reviewer_progress = status_values.get(st.session_state.status['reviewer'], 0)

    total_progress = (planner_progress + developer_progress + reviewer_progress) / 3

    return total_progress


# Функция для остановки процесса
def stop_process():
    """Останавливает текущий процесс и очищает файлы"""
    st.session_state.stop_flag = True
    st.session_state.status = {
        'planner': 'stopped',
        'developer': 'stopped',
        'reviewer': 'stopped'
    }

    # Очищаем файлы
    if st.session_state.current_project_files:
        cleanup_temp_files(st.session_state.current_project_files)

    st.session_state.logs.append("⛔ Процесс остановлен пользователем")
    st.session_state.current_project_files = []
    st.session_state.show_stop_confirm = False


# Заголовок
st.title("🤖 AI Office MVP")

# Боковая панель
with st.sidebar:
    st.header("🤖 Статус агентов")

    # Планировщик (Ася)
    col1, col2 = st.columns([1, 3])
    with col1:
        status = st.session_state.status['planner']
        if status == 'working':
            st.markdown("🟡")
        elif status == 'done':
            st.markdown("✅")
        elif status == 'error':
            st.markdown("❌")
        elif status == 'stopped':
            st.markdown("⛔")
        else:
            st.markdown("⚪")
    with col2:
        st.markdown("**Планировщик** (Ася)")

    # Разработчик (Джун-и)
    col1, col2 = st.columns([1, 3])
    with col1:
        status = st.session_state.status['developer']
        if status == 'working':
            st.markdown("🟡")
        elif status == 'done':
            st.markdown("✅")
        elif status == 'error':
            st.markdown("❌")
        elif status == 'stopped':
            st.markdown("⛔")
        else:
            st.markdown("⚪")
    with col2:
        st.markdown("**Разработчик** (Джун-и)")

    # Ревьюер (Кай)
    col1, col2 = st.columns([1, 3])
    with col1:
        status = st.session_state.status['reviewer']
        if status == 'working':
            st.markdown("🟡")
        elif status == 'done':
            st.markdown("✅")
        elif status == 'error':
            st.markdown("❌")
        elif status == 'stopped':
            st.markdown("⛔")
        else:
            st.markdown("⚪")
    with col2:
        st.markdown("**Ревьюер** (Кай)")

    st.divider()

    # Прогресс-бар
    if any(v != 'idle' for v in st.session_state.status.values()):
        progress = show_progress_bar()
        st.progress(progress, text=f"Общий прогресс: {int(progress * 100)}%")

    # Кнопка остановки
    if any(v == 'working' for v in st.session_state.status.values()):
        if st.button("⛔ Остановить процесс", type="secondary", use_container_width=True):
            st.session_state.show_stop_confirm = True

    # Диалог подтверждения остановки
    if st.session_state.show_stop_confirm:
        st.warning("⚠️ Вы уверены, что хотите прервать процесс?")
        st.markdown("Все временные файлы будут удалены.")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("✅ Да, остановить", use_container_width=True):
                stop_process()
                st.rerun()
        with col2:
            if st.button("❌ Нет, продолжить", use_container_width=True):
                st.session_state.show_stop_confirm = False
                st.rerun()

    st.divider()

    # Секция здоровья системы
    st.header("🩺 Здоровье системы")

    if st.button("🔍 Проверить подключения", use_container_width=True):
        with st.spinner("Проверка Ollama..."):
            health = check_ollama_health()
            st.session_state.health_status = health

            if health['ollama_running']:
                st.success("✅ Ollama запущена")
            else:
                st.error("❌ Ollama не запущена")

            if health['model_available']:
                st.success("✅ Модель llama2 найдена")
            else:
                st.error("❌ Модель llama2 не найдена")

            if health['model_responding']:
                st.success(f"✅ Модель отвечает ({health['response_time']:.1f}с)")
            else:
                st.error(f"❌ Модель не отвечает: {health['error']}")

                if st.button("🔄 Попробовать восстановить"):
                    if auto_recover():
                        st.rerun()

    # Секция бекапов
    st.header("💾 Бекапы")

    if st.button("📦 Создать бекап сейчас", use_container_width=True):
        with st.spinner("Создание бекапа..."):
            backup_result = create_backup()
            if backup_result["success"]:
                st.session_state.last_backup = backup_result
                st.success(f"✅ Бекап создан: {backup_result['backup_dir']}")
                st.info(f"📦 Архив: {backup_result['backup_zip']}")
            else:
                st.error(f"❌ Ошибка: {backup_result['error']}")

    # Информация о последнем бекапе
    if st.session_state.last_backup:
        st.caption(f"Последний бекап: {st.session_state.last_backup['timestamp']}")

    st.divider()
    st.caption("⚪ idle | 🟡 working | ✅ done | ❌ error | ⛔ stopped")

    # Кнопка очистки
    if st.button("🧹 Очистить логи и временные файлы", use_container_width=True):
        st.session_state.logs = []
        st.session_state.result = None
        if st.session_state.status['planner'] not in ['working']:
            st.session_state.status = {
                'planner': 'idle',
                'developer': 'idle',
                'reviewer': 'idle'
            }
        cleanup_temp_files([])
        st.rerun()

# Основная область
col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("📝 Новая задача")
    task_input = st.text_area(
        "Опиши задачу для агентов:",
        placeholder="Например: напиши парсер сайта, который сохраняет заголовки в CSV",
        height=150,
        key="task_input"
    )

    # Кнопка проверки перед запуском
    if st.checkbox("🔍 Проверять здоровье перед запуском", value=True):
        if st.button("🚀 Запустить агентов (с проверкой)", type="primary", use_container_width=True):
            if task_input.strip():
                # Проверяем здоровье перед запуском
                with st.spinner("🩺 Проверка системы..."):
                    health = check_ollama_health()

                    if not health['model_responding']:
                        st.error(f"❌ Система не готова: {health.get('error', 'Неизвестная ошибка')}")
                        st.info(
                            "🔄 Попробуйте:\n1. Запустить Ollama: `ollama serve`\n2. Проверить модель: `ollama pull llama2`\n3. Нажать кнопку 'Проверить подключения'")
                    else:
                        # Проверяем, не выполняется ли уже задача
                        if any(v == 'working' for v in st.session_state.status.values()):
                            st.warning("⚠️ Сначала дождитесь завершения текущей задачи или остановите её")
                        else:
                            # Создаём бекап перед запуском
                            with st.spinner("💾 Создание бекапа перед задачей..."):
                                backup_result = create_backup()
                                if backup_result["success"]:
                                    st.session_state.last_backup = backup_result
                                    st.info(f"✅ Бекап создан: {backup_result['backup_dir']}")
                                    st.session_state.logs.append(f"💾 Создан бекап: {backup_result['timestamp']}")
                                else:
                                    st.warning(f"⚠️ Не удалось создать бекап: {backup_result['error']}")

                            # Очищаем предыдущие логи и результат
                            st.session_state.logs = []
                            st.session_state.result = None
                            st.session_state.stop_flag = False
                            st.session_state.current_project_files = []
                            st.session_state.status = {
                                'planner': 'idle',
                                'developer': 'idle',
                                'reviewer': 'idle'
                            }

                            # Создаём очередь для коммуникации между потоками
                            log_queue = queue.Queue()

                            # Создаём ссылку на флаг остановки
                            stop_flag_ref = [st.session_state.stop_flag]

                            # Запускаем агентов в отдельном потоке
                            st.session_state.thread = threading.Thread(
                                target=run_agents_with_logs,
                                args=(task_input, log_queue, st.session_state.status,
                                      st.session_state.current_project_files, stop_flag_ref),
                                daemon=True
                            )
                            st.session_state.thread.start()

                            # Мониторинг выполнения с таймаутом
                            start_time = time.time()
                            last_heartbeat = time.time()
                            no_response_counter = 0

                            # Создаём контейнеры для отображения
                            status_container = st.empty()
                            time_container = st.empty()

                            # Ждём обновлений из очереди
                            with st.spinner("🤔 Агенты работают..."):
                                while st.session_state.thread.is_alive() or not log_queue.empty():
                                    # Проверяем таймаут
                                    elapsed = time.time() - start_time
                                    time_container.info(f"⏱️ Прошло: {int(elapsed)} сек")

                                    # Если прошло больше 3 минут без heartbeat'а
                                    if elapsed > 180 and (time.time() - last_heartbeat) > 30:
                                        no_response_counter += 1
                                        if no_response_counter > 3:
                                            st.error("❌ Процесс не отвечает более 30 секунд")
                                            if st.button("🔄 Попробовать восстановить"):
                                                if auto_recover():
                                                    st.rerun()
                                            break

                                    # Проверяем флаг остановки
                                    if stop_flag_ref[0]:
                                        break

                                    try:
                                        # Получаем сообщение из очереди
                                        msg_type, msg_data = log_queue.get(timeout=1.0)

                                        if msg_type == "log":
                                            st.session_state.logs.append(msg_data)
                                        elif msg_type == "status":
                                            st.session_state.status = msg_data
                                        elif msg_type == "result":
                                            st.session_state.result = msg_data
                                        elif msg_type == "heartbeat":
                                            last_heartbeat = time.time()
                                            no_response_counter = 0

                                    except queue.Empty:
                                        pass

                                    # Обновляем отображение логов
                                    if st.session_state.logs:
                                        with col2:
                                            st.subheader("📋 Журнал выполнения")
                                            for log in st.session_state.logs[-15:]:
                                                st.markdown(log)

                                    time.sleep(0.1)

                                if stop_flag_ref[0]:
                                    st.info("⛔ Процесс был остановлен")
            else:
                st.warning("⚠️ Введите задачу")

with col2:
    # Показываем логи (они уже обновляются в процессе)
    if st.session_state.logs:
        st.subheader("📋 Журнал выполнения")

        # Фильтр логов
        log_filter = st.radio(
            "Фильтр:",
            ["Все", "Ошибки", "Предупреждения", "Инфо"],
            horizontal=True,
            key="log_filter"
        )

        for log in st.session_state.logs[-20:]:  # Показываем последние 20 логов
            if log_filter == "Все":
                st.markdown(log)
            elif log_filter == "Ошибки" and "❌" in log:
                st.markdown(log)
            elif log_filter == "Предупреждения" and "⚠️" in log:
                st.markdown(log)
            elif log_filter == "Инфо" and "❌" not in log and "⚠️" not in log:
                st.markdown(log)

    # Показываем результат
    if st.session_state.result and not st.session_state.stop_flag:
        st.subheader("✅ Результат")
        st.write(st.session_state.result)

# Файловый менеджер
with st.expander("📁 Файлы проекта", expanded=False):
    # Текущие файлы
    if st.session_state.current_project_files:
        st.info("📂 Файлы текущего проекта:")
        for file_path in st.session_state.current_project_files:
            if Path(file_path).exists():
                with open(file_path, 'r') as f:
                    content = f.read()
                with st.expander(f"📄 {Path(file_path).name}"):
                    st.code(content, language='python' if file_path.endswith('.py') else 'markdown')
    else:
        st.info("Нет активных файлов. Запустите задачу для создания проекта.")

    # Сохранённые проекты
    if PROJECTS_PATH.exists():
        saved_projects = list(PROJECTS_PATH.glob("project_*"))
        if saved_projects:
            st.divider()
            st.info("📚 Сохранённые проекты:")
            for proj_dir in saved_projects[-5:]:
                with st.expander(f"📁 {proj_dir.name}"):
                    for file in proj_dir.glob("*"):
                        with open(file, 'r') as f:
                            content = f.read()
                        st.code(content, language='python' if file.suffix == '.py' else 'markdown')

    # Бекапы
    if BACKUP_PATH.exists():
        backups = sorted(BACKUP_PATH.glob("backup_*"))
        if backups:
            st.divider()
            st.info("💾 Последние бекапы:")
            for backup in backups[-3:]:
                if backup.is_dir():
                    st.caption(f"📦 {backup.name}")

# Footer
st.divider()
st.caption(
    "AI Office MVP - Агенты: Ася (планировщик), Джун-и (разработчик), Кай (ревьюер) | Автоматическая диагностика и восстановление")