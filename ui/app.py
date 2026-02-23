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
import json

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

# Инициализация session state
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
    'progress': {'planner': 0, 'developer': 0, 'reviewer': 0, 'total': 0},
    'project_manager': None,
    'dialog_messages': [],
    'dialog_active': False,
    'waiting_for_response': False,
    'final_spec': None,
    'show_dialog_history': False,
    'task_from_spec': None,
    'start_time': None,
    'log_queue': None
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

        # ИСПРАВЛЕНИЕ 1: Безопасная проверка final_spec
        try:
            has_spec = st.session_state.get('final_spec', None) is not None
        except:
            has_spec = False

        # ИСПРАВЛЕНИЕ 2: result объявляем до использования
        result = None

        if has_spec:
            try:
                spec = st.session_state.final_spec
                result = run_crew(task, spec)
            except Exception as e:
                log_queue.put(("log", f"⚠️ Ошибка с ТЗ: {str(e)[:50]}, запускаю без ТЗ"))
                result = run_crew(task)
        else:
            result = run_crew(task)

        if stop_flag_ref[0]: return

        # Проверяем, что result не пустой
        if result is None:
            log_queue.put(("log", "❌ run_crew вернул None"))
            return

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
        import traceback
        log_queue.put(("log", f"📋 Детали: {traceback.format_exc()[:200]}"))


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


# Добавляем стили для современного чата
st.markdown("""
<style>
    /* Современный стиль для чата */
    .chat-message {
        padding: 1rem;
        border-radius: 10px;
        margin-bottom: 1rem;
        animation: fadeIn 0.3s ease-in;
    }

    .user-message {
        background: linear-gradient(135deg, #2b2b2b 0%, #1a1a1a 100%);
        border-left: 4px solid #4CAF50;
    }

    .system-message {
        background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
        border-left: 4px solid #2196F3;
    }

    .timestamp {
        font-size: 0.8rem;
        color: #888;
        margin-top: 0.5rem;
    }

    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(10px); }
        to { opacity: 1; transform: translateY(0); }
    }

    /* Стили для typing индикатора */
    .typing-indicator {
        display: inline-block;
        padding: 1rem;
        background: rgba(255,255,255,0.1);
        border-radius: 20px;
    }

    .typing-dot {
        display: inline-block;
        width: 8px;
        height: 8px;
        border-radius: 50%;
        background: #fff;
        margin: 0 2px;
        animation: typing 1.4s infinite ease-in-out;
    }

    .typing-dot:nth-child(2) { animation-delay: 0.2s; }
    .typing-dot:nth-child(3) { animation-delay: 0.4s; }

    @keyframes typing {
        0%, 60%, 100% { transform: translateY(0); }
        30% { transform: translateY(-10px); }
    }
</style>
""", unsafe_allow_html=True)

# Заголовок
st.title("🤖 AI Office MVP")

# Боковая панель
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

    if st.button("📋 Показать логи сессии", use_container_width=True):
        subprocess.Popen(["streamlit", "run", "view_logs.py"])
        st.success("✅ Просмотр логов открыт")

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

    # Поле ввода задачи
    default_task = st.session_state.get('test_task', '')
    task_input = st.text_area(
        "Задача:",
        value=default_task,
        placeholder="Опишите задачу...",
        height=100,
        key="task_input"
    )

    # ===== ВЫБОР РЕЖИМА =====
    st.divider()

    # Кнопки выбора режима
    mode_col1, mode_col2 = st.columns(2)

    with mode_col1:
        start_with_dialog = st.button("💬 Начать диалог с менеджером",
                                      use_container_width=True,
                                      disabled=st.session_state.is_running,
                                      help="Сначала обсудить детали с менеджером, затем запустить агентов")

    with mode_col2:
        start_agents_now = st.button("🚀 Запустить агентов сразу",
                                     use_container_width=True,
                                     type="primary" if not st.session_state.dialog_active else "secondary",
                                     disabled=st.session_state.is_running,
                                     help="Запустить агентов с текущим промптом без обсуждения")

    # Обработка выбора
    if start_with_dialog and task_input.strip() and not st.session_state.is_running:
        from agents.project_manager import ProjectManager

        st.session_state.project_manager = ProjectManager()
        first_message = st.session_state.project_manager.start_dialog(task_input)
        st.session_state.dialog_messages = st.session_state.project_manager.dialog_history
        st.session_state.dialog_active = True
        st.session_state.waiting_for_response = True
        st.rerun()

    # Запуск агентов сразу
    if start_agents_now and task_input.strip() and not st.session_state.is_running:
        st.session_state.start_agents = True
        st.rerun()

    # ===== ДИАЛОГ С МЕНЕДЖЕРОМ =====
    if st.session_state.dialog_active and st.session_state.project_manager:

        # Контейнер для сообщений
        chat_container = st.container()

        with chat_container:
            for msg in st.session_state.dialog_messages:
                role_class = "user-message" if msg['role'] == 'user' else "system-message"

                st.markdown(f"""
                <div class="chat-message {role_class}">
                    <strong>{'👤 Вы' if msg['role'] == 'user' else '🤖 Менеджер'}</strong>
                    <div style="margin-top: 0.5rem;">{msg['message']}</div>
                    <div class="timestamp">{msg['timestamp'][11:16]}</div>
                </div>
                """, unsafe_allow_html=True)

            # Индикатор печатания
            if st.session_state.waiting_for_response:
                st.markdown("""
                <div class="typing-indicator">
                    <span class="typing-dot"></span>
                    <span class="typing-dot"></span>
                    <span class="typing-dot"></span>
                </div>
                """, unsafe_allow_html=True)

        # Поле для ответа
        user_response = st.text_area(
            "Ваше сообщение:",
            placeholder="Напишите сообщение... (можно просто текст, без формальностей)",
            key="dialog_response",
            height=100
        )

        # Кнопки управления диалогом
        col_a, col_b, col_c, col_d = st.columns([2, 1, 1, 1])

        with col_a:
            if st.button("📤 Отправить", use_container_width=True, type="primary"):
                if user_response.strip():
                    st.session_state.waiting_for_response = False
                    result = st.session_state.project_manager.process_response(user_response)
                    st.session_state.dialog_messages = st.session_state.project_manager.dialog_history

                    if result['status'] == 'ready':
                        st.session_state.dialog_active = False
                        st.session_state.final_spec = result['spec']
                        st.session_state.waiting_for_response = False
                        st.success("✅ ТЗ готово! Можно запускать агентов.")
                    else:
                        st.session_state.waiting_for_response = True
                    st.rerun()

        with col_b:
            if st.button("🚀 Запуск", use_container_width=True):
                final_spec = st.session_state.project_manager._generate_final_spec()
                st.session_state.final_spec = final_spec
                st.session_state.dialog_active = False
                st.session_state.waiting_for_response = False
                st.rerun()

        with col_c:
            if st.button("❌ Отмена", use_container_width=True):
                st.session_state.dialog_active = False
                st.session_state.project_manager = None
                st.session_state.waiting_for_response = False
                st.rerun()

        with col_d:
            if st.button("📋 История", use_container_width=True):
                dialog_dir = Path("dialog_history")
                if dialog_dir.exists():
                    dialogs = list(dialog_dir.glob("*.json"))
                    st.session_state.show_dialog_history = True
                    st.rerun()

    # ===== ОТОБРАЖЕНИЕ ИСТОРИИ ДИАЛОГОВ =====
    if st.session_state.get('show_dialog_history', False):
        with st.expander("📚 История диалогов", expanded=True):
            dialog_dir = Path("dialog_history")
            if dialog_dir.exists():
                dialogs = sorted(dialog_dir.glob("*.json"), reverse=True)[:10]
                for dialog_file in dialogs:
                    with open(dialog_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    col_x, col_y = st.columns([3, 1])
                    with col_x:
                        st.caption(f"📅 {data['timestamp'][:16]} | Сообщений: {data['message_count']}")
                        st.write(f"**Задача:** {data['requirements']['initial_task'][:50]}...")
                    with col_y:
                        if st.button("📎 Загрузить", key=f"load_{dialog_file.stem}"):
                            from agents.project_manager import ProjectManager

                            pm = ProjectManager()
                            pm.load_previous_dialog(dialog_file.stem.replace("dialog_", ""))
                            st.session_state.project_manager = pm
                            st.session_state.dialog_messages = pm.dialog_history
                            st.session_state.dialog_active = True
                            st.session_state.waiting_for_response = True
                            st.session_state.show_dialog_history = False
                            st.rerun()
                    st.divider()

    # ===== ОТОБРАЖЕНИЕ ФИНАЛЬНОГО ТЗ =====
    if st.session_state.final_spec:
        with st.expander("📋 Техническое задание", expanded=True):
            st.markdown(st.session_state.final_spec)

            if st.button("📌 Использовать это ТЗ для задачи", use_container_width=True):
                st.session_state.task_from_spec = st.session_state.final_spec
                st.success("✅ ТЗ готово! Можете запускать агентов")

    # ===== ЗАПУСК АГЕНТОВ =====
    if st.session_state.get('start_agents', False) and not st.session_state.is_running:
        st.session_state.start_agents = False
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
            st.session_state.progress = {'planner': 0, 'developer': 0, 'reviewer': 0, 'total': 0}
            st.session_state.start_time = time.time()

            log_queue = queue.Queue()
            st.session_state.log_queue = log_queue
            stop_flag_ref = [st.session_state.stop_flag]

            st.session_state.thread = threading.Thread(
                target=run_agents_with_logs,
                args=(task_input, log_queue, st.session_state.status,
                      st.session_state.current_project_files, stop_flag_ref),
                daemon=True
            )
            st.session_state.thread.start()

    # ===== ОТОБРАЖЕНИЕ ПРОГРЕССА АГЕНТОВ =====
    if st.session_state.is_running:
        # Создаем контейнеры для живого прогресса
        progress_container = st.container()

        with progress_container:
            # Показываем текущий статус
            col_s1, col_s2, col_s3 = st.columns(3)
            with col_s1:
                status_emoji = {
                    'idle': '⚪', 'working': '🟡', 'done': '✅', 'error': '❌', 'stopped': '⛔'
                }
                st.markdown(f"{status_emoji.get(st.session_state.status['planner'], '⚪')} Планировщик")
            with col_s2:
                st.markdown(f"{status_emoji.get(st.session_state.status['developer'], '⚪')} Разработчик")
            with col_s3:
                st.markdown(f"{status_emoji.get(st.session_state.status['reviewer'], '⚪')} Ревьюер")

            # Прогресс-бары
            st.progress(st.session_state.progress['planner'] / 100,
                        text=f"Планировщик: {st.session_state.progress['planner']}%")
            st.progress(st.session_state.progress['developer'] / 100,
                        text=f"Разработчик: {st.session_state.progress['developer']}%")
            st.progress(st.session_state.progress['reviewer'] / 100,
                        text=f"Ревьюер: {st.session_state.progress['reviewer']}%")
            st.progress(st.session_state.progress['total'] / 100, text=f"Общий: {st.session_state.progress['total']}%")

            # Таймер
            if 'start_time' in st.session_state:
                elapsed = int(time.time() - st.session_state.start_time)
                st.info(f"⏱️ Прошло: {elapsed} сек")

            # Последние логи
            if st.session_state.logs:
                with st.expander("📋 Последние логи", expanded=True):
                    for log in st.session_state.logs[-5:]:
                        st.caption(log)

        # Проверяем очередь
        if st.session_state.thread and hasattr(st.session_state, 'log_queue'):
            try:
                msg_type, msg_data = st.session_state.log_queue.get(timeout=0.1)

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
                elif msg_type == "result":
                    st.session_state.result = msg_data
                    st.session_state.is_running = False
                    st.session_state.session_logger.log_chat("Агенты", str(msg_data)[:200])
                    st.success("✅ Готово!")
            except queue.Empty:
                pass

            # Проверяем завершение потока
            if not st.session_state.thread.is_alive() and st.session_state.is_running:
                st.session_state.is_running = False
                if not st.session_state.result:
                    st.error("❌ Задача завершилась без результата")

        # Автоматическое обновление
        time.sleep(0.5)
        st.rerun()

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
        for file_path in st.session_state.current_project_files[-3:]:
            if Path(file_path).exists():
                st.caption(f"📄 {Path(file_path).name}")

# Footer
st.divider()
st.caption("🤖 Ася | Джун-и | Кай | Менеджер • ⚡ С диалогом и ТЗ")