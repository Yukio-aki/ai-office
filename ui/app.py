import sys
from pathlib import Path

# Добавляем корень проекта в PYTHONPATH
ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT))

import streamlit as st
from core.crew_runner import run_crew

st.set_page_config(page_title="AI Office")

st.title("🤖 AI Office MVP")

task_input = st.text_area(
    "Поставь задачу агентам",
    placeholder="Например: сделай парсер сайта..."
)
#Comment

if st.button("Запустить"):
    if task_input.strip():
        with st.spinner("Агенты работают..."):
            result = run_crew(task_input)
        st.success("Готово!")
        st.write(result)