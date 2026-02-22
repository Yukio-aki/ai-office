import streamlit as st
from pathlib import Path
from datetime import datetime
import json

st.set_page_config(page_title="Session Logs Viewer", page_icon="📋", layout="wide")

st.title("📋 Просмотр логов сессий")

log_dir = Path("session_logs")
if not log_dir.exists():
    st.warning("Нет сохранённых логов")
    st.stop()

# Получаем все сессии
sessions = {}
for file in log_dir.glob("session_*.log"):
    session_id = file.stem.replace("session_", "")
    if session_id not in sessions:
        sessions[session_id] = {
            'logs': [],
            'chats': [],
            'errors': [],
            'states': []
        }

for file in log_dir.glob("*"):
    if file.is_file():
        for session_id in sessions.keys():
            if session_id in file.name:
                if 'chat' in file.name:
                    sessions[session_id]['chats'].append(file)
                elif 'errors' in file.name:
                    sessions[session_id]['errors'].append(file)
                elif 'state' in file.name:
                    sessions[session_id]['states'].append(file)
                else:
                    sessions[session_id]['logs'].append(file)

# Выбор сессии
selected_session = st.selectbox(
    "Выберите сессию:",
    sorted(sessions.keys(), reverse=True)
)

if selected_session:
    tab1, tab2, tab3, tab4 = st.tabs(["📊 Обзор", "📝 Логи", "💬 Чат", "❌ Ошибки"])

    with tab1:
        st.subheader("Файлы сессии")
        files = sessions[selected_session]

        col1, col2 = st.columns(2)
        with col1:
            st.metric("Лог-файлы", len(files['logs']))
            st.metric("Чат-файлы", len(files['chats']))
        with col2:
            st.metric("Файлы ошибок", len(files['errors']))
            st.metric("State-файлы", len(files['states']))

        # Показываем state если есть
        if files['states']:
            st.subheader("Последнее состояние")
            with open(files['states'][0], 'r', encoding='utf-8') as f:
                state = json.load(f)
            st.json(state)

    with tab2:
        if files['logs']:
            for log_file in files['logs']:
                with st.expander(f"📄 {log_file.name}"):
                    with open(log_file, 'r', encoding='utf-8') as f:
                        st.text(f.read())
        else:
            st.info("Нет лог-файлов")

    with tab3:
        if files['chats']:
            for chat_file in files['chats']:
                with st.expander(f"💬 {chat_file.name}"):
                    with open(chat_file, 'r', encoding='utf-8') as f:
                        st.markdown(f.read())
        else:
            st.info("Нет чат-файлов")

    with tab4:
        if files['errors']:
            for error_file in files['errors']:
                with st.expander(f"❌ {error_file.name}"):
                    with open(error_file, 'r', encoding='utf-8') as f:
                        st.code(f.read(), language='text')
        else:
            st.info("Нет ошибок")

# Кнопка для создания отчета
if st.button("📊 Создать отчет для отправки"):
    # Собираем все логи последней сессии
    latest_session = sorted(sessions.keys(), reverse=True)[0]
    report_file = log_dir / f"report_{latest_session}.md"

    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(f"# Отчет о сессии {latest_session}\n\n")
        f.write(f"Создан: {datetime.now()}\n\n")

        # Добавляем чат
        if sessions[latest_session]['chats']:
            f.write("## Чат\n\n")
            with open(sessions[latest_session]['chats'][0], 'r', encoding='utf-8') as chat:
                f.write(chat.read())

        # Добавляем ошибки
        if sessions[latest_session]['errors']:
            f.write("\n## Ошибки\n\n")
            with open(sessions[latest_session]['errors'][0], 'r', encoding='utf-8') as err:
                f.write(f"```\n{err.read()}\n```")

        # Добавляем состояние
        if sessions[latest_session]['states']:
            f.write("\n## Состояние\n\n")
            f.write("```json\n")
            with open(sessions[latest_session]['states'][0], 'r', encoding='utf-8') as state:
                f.write(state.read())
            f.write("\n```\n")

    st.success(f"✅ Отчет создан: {report_file}")

    # Кнопка для скачивания
    with open(report_file, 'r', encoding='utf-8') as f:
        st.download_button(
            "📥 Скачать отчет",
            f.read(),
            file_name=f"session_report_{latest_session}.md",
            mime="text/markdown"
        )