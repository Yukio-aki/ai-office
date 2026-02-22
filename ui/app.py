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
from session_logger import get_logger, end_session

# Настройка страницы
st.set_page_config(page_title="AI Office", page_icon="🤖", layout="wide")

# Пути
BACKUP_PATH = Path("C:/Users/Aki/Desktop/Need/Need/MyProject_AI-office/Backup")
PROJECTS_PATH = ROOT / "workspace" / "projects"
TEMP_PATH = ROOT / "workspace" / "temp"

# Инициализация session state (оптимизированная)
DEFAULT_STATE = {
    'logs': [],
    'status': {'planner': 'idle', 'developer': 'idle', 'reviewer': 'idle'},
    'result': None,
    'result_raw': None,
    'thread': None,
    'stop_flag': False,
    'current_project_files': [],
    'show_stop_confirm': False,
    'last_backup': None,
    'health_status': None,
    'last_heartbeat': time.time(),
    'is_running': False,
    'session_logger': None,
    'progress': {'planner': 0, 'developer': 0, 'reviewer': 0, 'total': 0}
}

for key, value in DEFAULT_STATE.items():
    if key not in st.session_state:
        st.session_state[key] = value

# Инициализация логгера сессии
if st.session_state.session_logger is None:
    st.session_state.session_logger = get_logger()
    st.session_state.session_logger.log("🚀 Streamlit UI запущен")


# Кэш для проверки здоровья (обновляется раз в 30 секунд)
@st.cache_data(ttl=30)
def cached_health_check():
    """Кэшированная проверка здоровья"""
    return check_ollama_health()


def check_ollama_health():
    """Быстрая проверка здоровья Ollama"""
    health_report = {
        'ollama_running': False,
        'model_available': False,
        'model_responding': False,
        'response_time': None,
        'error': None
    }

    try:
        start = time.time()
        # Быстрая проверка только наличия сервера
        response = requests.get("http://localhost:11434/api/tags", timeout=2)

        if response.status_code == 200:
            health_report['ollama_running'] = True
            health_report['model_available'] = True
            health_report['model_responding'] = True
            health_report['response_time'] = time.time() - start
    except:
        health_report['error'] = "Ollama не отвечает"

    return health_report


def auto_recover():
    """Быстрое восстановление"""
    st.session_state.logs.append("🔄 Восстановление...")
    try:
        subprocess.run(['taskkill', '/F', '/IM', 'ollama.exe'], capture_output=True)
        time.sleep(1)
        subprocess.Popen(['ollama', 'serve'], creationflags=subprocess.CREATE_NO_WINDOW)
        time.sleep(3)
        return True
    except:
        return False


def run_agents_with_logs(task, log_queue, status_dict, project_files_list, stop_flag_ref):
    """Оптимизированная версия с меньшим количеством логов"""

    def heartbeat():
        log_queue.put(("heartbeat", time.time()))

    heartbeat()

    temp_dir = TEMP_PATH / f"project_{int(time.time())}"
    temp_dir.mkdir(parents=True, exist_ok=True)

    try:
        # Минимальная проверка здоровья
        health = check_ollama_health()
        if not health['model_responding']:
            log_queue.put(("log", "❌ Ollama не отвечает"))
            return

        # Планировщик
        if stop_flag_ref[0]: return
        status_dict['planner'] = 'working'
        log_queue.put(("status", status_dict.copy()))
        log_queue.put(("progress", {'planner': 30, 'total': 10}))

        result = run_crew(task)

        if stop_flag_ref[0]: return

        # Разработчик
        status_dict['planner'] = 'done'
        status_dict['developer'] = 'working'
        log_queue.put(("status", status_dict.copy()))
        log_queue.put(("progress", {'developer': 30, 'total': 50}))

        # Сохраняем результат
        code_file = temp_dir / "output.py"
        with open(code_file, 'w', encoding='utf-8') as f:
            if hasattr(result, 'raw'):
                f.write(result.raw)
                result_text = result.raw
            else:
                f.write(str(result))
                result_text = str(result)
        project_files_list.append(str(code_file))

        if stop_flag_ref[0]: return

        # После получения result = run_crew(task) добавь:
        log_queue.put(("log", "✅ Задача выполнена, передаю результат..."))
        log_queue.put(("result", result_text))
        log_queue.put(("status", {'planner': 'done', 'developer': 'done', 'reviewer': 'done'}))

        # Ревьюер
        status_dict['developer'] = 'done'
        status_dict['reviewer'] = 'working'
        log_queue.put(("status", status_dict.copy()))
        log_queue.put(("progress", {'reviewer': 30, 'total': 80}))

        time.sleep(0.5)  # Минимальная задержка

        status_dict['reviewer'] = 'done'
        log_queue.put(("status", status_dict.copy()))
        log_queue.put(("progress", {'total': 100}))
        log_queue.put(("result", result_text))

        # Сохраняем проект (в фоне)
        if not stop_flag_ref[0]:
            project_name = f"project_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            project_dir = PROJECTS_PATH / project_name
            project_dir.mkdir(parents=True, exist_ok=True)
            for file_path in project_files_list:
                shutil.copy2(Path(file_path), project_dir)

    except Exception as e:
        log_queue.put(("log", f"❌ Ошибка: {str(e)[:100]}"))


def update_progress_bars():
    """Обновляет прогресс-бары на основе статусов"""
    status_to_progress = {
        'idle': 0,
        'working': 50,
        'done': 100,
        'error': 0,
        'stopped': 0
    }

    st.session_state.progress['planner'] = status_to_progress.get(st.session_state.status['planner'], 0)
    st.session_state.progress['developer'] = status_to_progress.get(st.session_state.status['developer'], 0)
    st.session_state.progress['reviewer'] = status_to_progress.get(st.session_state.status['reviewer'], 0)

    total = (st.session_state.progress['planner'] +
             st.session_state.progress['developer'] +
             st.session_state.progress['reviewer']) / 3
    st.session_state.progress['total'] = int(total)


def stop_process():
    """Быстрая остановка процесса"""
    st.session_state.stop_flag = True
    st.session_state.status = {'planner': 'stopped', 'developer': 'stopped', 'reviewer': 'stopped'}
    st.session_state.is_running = False
    if st.session_state.current_project_files:
        cleanup_temp_files(st.session_state.current_project_files)
    st.session_state.current_project_files = []
    st.session_state.show_stop_confirm = False


# Заголовок
st.title("🤖 AI Office MVP")

# Боковая панель (оптимизированная)
with st.sidebar:
    st.header("🤖 Прогресс агентов")

    # Прогресс-бары для каждого агента
    update_progress_bars()

    st.progress(st.session_state.progress['planner'] / 100,
                text=f"📋 Планировщик (Ася): {st.session_state.progress['planner']}%")
    st.progress(st.session_state.progress['developer'] / 100,
                text=f"💻 Разработчик (Джун-и): {st.session_state.progress['developer']}%")
    st.progress(st.session_state.progress['reviewer'] / 100,
                text=f"🔍 Ревьюер (Кай): {st.session_state.progress['reviewer']}%")

    st.divider()
    st.progress(st.session_state.progress['total'] / 100,
                text=f"📊 Общий прогресс: {st.session_state.progress['total']}%")

    if any(v == 'working' for v in st.session_state.status.values()):
        if st.button("⛔ Остановить", type="secondary", use_container_width=True):
            st.session_state.show_stop_confirm = True

    if st.session_state.show_stop_confirm:
        st.warning("Прервать?")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("✅ Да", use_container_width=True):
                stop_process()
                st.rerun()
        with col2:
            if st.button("❌ Нет", use_container_width=True):
                st.session_state.show_stop_confirm = False
                st.rerun()

    st.divider()

    # Компактная информация о системе
    with st.expander("🩺 Система", expanded=False):
        health = cached_health_check()
        if health['ollama_running']:
            st.success("✅ Ollama OK")
        else:
            st.error("❌ Ollama не отвечает")
            if st.button("🔄 Восстановить"):
                if auto_recover():
                    st.rerun()

    with st.expander("💾 Бекапы", expanded=False):
        if st.button("📦 Создать бекап", use_container_width=True):
            with st.spinner("..."):
                backup_result = create_backup(async_mode=True)
                st.success("✅ Бекап создан")

    if st.button("🧹 Очистить", use_container_width=True):
        st.session_state.logs = []
        st.session_state.result = None
        st.session_state.status = {'planner': 'idle', 'developer': 'idle', 'reviewer': 'idle'}
        cleanup_temp_files([])
        st.rerun()

    if st.button("🛑 Завершить сессию", use_container_width=True):
        end_session()
        st.success("✅ Логи сохранены")

# Основная область
col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("📝 Новая задача")

    # Компактные кнопки тестов
    test_col1, test_col2 = st.columns(2)
    with test_col1:
        if st.button("🧪 Тест", use_container_width=True):
            st.session_state.test_task = "Скажи 'Привет' и напиши hello_world()"
            st.rerun()
    with test_col2:
        if st.button("🎨 Сайт", use_container_width=True):
            st.session_state.test_task = "Создай простую HTML страницу с темным фоном"
            st.rerun()

    task_input = st.text_area(
        "Задача:",
        value=st.session_state.get('test_task', ''),
        placeholder="Опишите задачу...",
        height=100,
        key="task_input"
    )

    if st.button("🚀 Запустить", type="primary", use_container_width=True):
        if task_input.strip() and not st.session_state.is_running:
            st.session_state.is_running = True
            st.session_state.session_logger.log_chat("Пользователь", task_input[:100])

            # Быстрая проверка
            health = cached_health_check()
            if not health['model_responding']:
                st.error("❌ Ollama не отвечает")
                st.session_state.is_running = False
            else:
                # Бекап в фоне
                create_backup(async_mode=True)

                # Сброс состояния
                st.session_state.logs = []
                st.session_state.result = None
                st.session_state.stop_flag = False
                st.session_state.current_project_files = []
                st.session_state.status = {'planner': 'idle', 'developer': 'idle', 'reviewer': 'idle'}

                log_queue = queue.Queue()
                stop_flag_ref = [st.session_state.stop_flag]

                st.session_state.thread = threading.Thread(
                    target=run_agents_with_logs,
                    args=(task_input, log_queue, st.session_state.status,
                          st.session_state.current_project_files, stop_flag_ref),
                    daemon=True
                )
                st.session_state.thread.start()

                start_time = time.time()
                time_container = st.empty()

                # Быстрый цикл обновления
                while st.session_state.thread.is_alive() or not log_queue.empty():
                    if stop_flag_ref[0]:
                        break

                    try:
                        msg_type, msg_data = log_queue.get(timeout=0.1)

                        if msg_type == "log":
                            st.session_state.logs.append(msg_data)
                        elif msg_type == "status":
                            st.session_state.status = msg_data
                        elif msg_type == "progress":
                            if 'planner' in msg_data:
                                st.session_state.progress['planner'] = msg_data['planner']
                            if 'developer' in msg_data:
                                st.session_state.progress['developer'] = msg_data['developer']
                            if 'reviewer' in msg_data:
                                st.session_state.progress['reviewer'] = msg_data['reviewer']
                            if 'total' in msg_data:
                                st.session_state.progress['total'] = msg_data['total']
                            st.rerun()
                        elif msg_type == "result":
                            st.session_state.result = msg_data
                            st.session_state.session_logger.log("✅ Результат получен в UI")
                            st.session_state.session_logger.log_chat("Агенты", str(msg_data)[:200])
                            st.success("✅ Задача выполнена! Результат загружен.")
                            # Принудительно обновляем статусы
                            st.session_state.status = {
                                'planner': 'done',
                                'developer': 'done',
                                'reviewer': 'done'
                            }
                            st.session_state.progress = {
                                'planner': 100,
                                'developer': 100,
                                'reviewer': 100,
                                'total': 100
                            }
                            st.rerun()  # Обновляем UI
                    except queue.Empty:
                        pass

                    # Обновляем таймер
                    elapsed = int(time.time() - start_time)
                    time_container.info(f"⏱️ {elapsed} сек")

                    if elapsed > 180:  # 3 минуты таймаут
                        st.error("❌ Таймаут")
                        stop_process()
                        break

                    time.sleep(0.05)  # Уменьшено для скорости

                st.session_state.is_running = False

with col2:
    # Минимальные логи (только последние 5)
    if st.session_state.logs:
        with st.expander("📋 Логи", expanded=True):
            for log in st.session_state.logs[-5:]:
                st.caption(log)

    # Результат
    if st.session_state.result:
        with st.expander("✅ Результат", expanded=True):
            result_text = st.session_state.result
            if "```python" in result_text:
                import re

                code = re.findall(r'```python\n(.*?)```', result_text, re.DOTALL)
                if code:
                    st.code(code[0], language='python')
                else:
                    st.code(result_text, language='python')
            else:
                st.text(result_text[:500] + "..." if len(result_text) > 500 else result_text)

# Файловый менеджер (компактный)
with st.expander("📁 Файлы", expanded=False):
    if st.session_state.current_project_files:
        for file_path in st.session_state.current_project_files[-3:]:  # Только последние 3
            if Path(file_path).exists():
                st.caption(f"📄 {Path(file_path).name}")

# Footer
st.caption("🤖 Ася | Джун-и | Кай • ⚡ Оптимизированная версия")