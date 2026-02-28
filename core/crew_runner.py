import os
import shutil
from datetime import datetime
from pathlib import Path
from crewai import Crew, Task
import re
import json

# Пути
ROOT = Path(__file__).resolve().parent.parent
WORKSPACE_PATH = ROOT / "workspace"
PROJECTS_PATH = WORKSPACE_PATH / "projects"
TEMP_PATH = WORKSPACE_PATH / "temp"

# Настройки модели
os.environ["OPENAI_API_KEY"] = "ollama"
os.environ["OPENAI_API_BASE"] = "http://localhost:11434/v1"
os.environ["OPENAI_MODEL_NAME"] = "phi3:mini"


def log_step(message):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")


def parse_task_to_state(user_task: str):
    from core.state import ProjectState
    state = ProjectState(task=user_task)

    task_lower = user_task.lower()

    # Цвета
    if "черный" in task_lower or "black" in task_lower:
        state.colors.append("black")
    if "белый" in task_lower or "white" in task_lower:
        state.colors.append("white")

    # Анимация
    if "растет" in task_lower or "grow" in task_lower:
        state.animation_type = "grow"
    if "линия" in task_lower or "line" in task_lower:
        state.animation_element = "line"
    if "медлен" in task_lower:
        state.animation_speed = "slow"
    if "киберпанк" in task_lower or "cyberpunk" in task_lower:
        state.style = "cyberpunk"

    return state


def save_result(result_text, task_temp_dir, task_timestamp):
    # Извлекаем код из markdown
    if "```html" in result_text:
        code = re.search(r'```html\n(.*?)```', result_text, re.DOTALL)
        if code:
            result_text = code.group(1)

    html_file = task_temp_dir / "index.html"
    with open(html_file, 'w', encoding='utf-8') as f:
        f.write(result_text)

    project_dir = PROJECTS_PATH / f"PROJECT_{task_timestamp}"
    project_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(html_file, project_dir)

    return html_file, project_dir


def run_crew(user_task: str, refined_task: str = None):
    """Clarifier + Parser + Planner + Developer + Reviewer + Knowledge"""

    # Используем уточненный запрос если есть
    final_task = refined_task if refined_task else user_task

    log_step("=" * 60)
    log_step("🚀 CLARIFIER + PARSER + PLANNER + DEVELOPER + KNOWLEDGE + REVIEWER")
    log_step("=" * 60)

    task_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    task_temp_dir = TEMP_PATH / f"task_{task_timestamp}"
    task_temp_dir.mkdir(parents=True, exist_ok=True)

    try:
        # ===== PARSER =====
        state = parse_task_to_state(final_task)
        log_step(f"📋 Состояние: {state.to_json()}")

        # ===== PLANNER (усиленный) =====
        from agents.planner import create_planner
        planner = create_planner()

        # Добавляем контекст о стиле
        style_context = ""
        if hasattr(state, 'style') and state.style == "cyberpunk":
            style_context = " This is cyberpunk style with neon effects."

        planner_prompt = f"""Create architectural plan for: {state.to_prompt()}
Complexity: {state.complexity}
Animation: {state.animation_type}
Speed: {state.animation_speed}
Element: {state.animation_element}
Style: {style_context}

Output ONLY JSON plan."""

        planner_task = Task(
            description=planner_prompt,
            agent=planner,
            expected_output="JSON plan"
        )

        planner_crew = Crew(agents=[planner], tasks=[planner_task], verbose=False)
        tech_choice = planner_crew.kickoff()
        tech_text = tech_choice.raw if hasattr(tech_choice, 'raw') else str(tech_choice)

        # Парсим JSON план
        try:
            # Ищем JSON в ответе
            json_match = re.search(r'\{.*\}', tech_text, re.DOTALL)
            if json_match:
                plan = json.loads(json_match.group())
                tech_name = plan.get('tech_stack', ['html'])[0]
                file_structure = plan.get('file_structure', ['index.html'])
                log_step(f"📋 Архитектурный план: {json.dumps(plan, indent=2, ensure_ascii=False)}")
            else:
                # fallback
                tech_name = "html"
                file_structure = ['index.html']
        except Exception as e:
            log_step(f"⚠️ Ошибка парсинга JSON: {e}, использую fallback")
            tech_name = "html"
            file_structure = ['index.html']

        log_step(f"📌 Планировщик выбрал: {tech_name}")

        # ===== KNOWLEDGE SEARCH =====
        from core.knowledge_search import KnowledgeSearch
        searcher = KnowledgeSearch()

        # Ищем примеры
        keywords = []
        if state.animation_type:
            keywords.append(state.animation_type)
        if state.animation_element:
            keywords.append(state.animation_element)
        if state.colors:
            keywords.extend(state.colors)

        examples = searcher.search_by_tech(tech_name, keywords, max_results=2)
        rules = searcher.get_rules(max_rules=2)

        # Формируем контекст
        context = ""
        if examples:
            context += "\n\n=== ПРИМЕРЫ ===\n"
            for ex in examples:
                # Обрезаем длинные примеры для phi3
                content = ex['content']
                if len(content) > 1500:
                    content = content[:1500] + "\n<!-- truncated -->"
                context += f"\n-- {ex['description']} --\n{content}\n"

        if rules:
            context += "\n=== ПРАВИЛА ===\n"
            for rule in rules:
                context += f"- {rule}\n"

        # ===== DEVELOPER =====
        from agents.developer import create_developer
        developer = create_developer()

        dev_prompt = f"""Generate COMPLETE HTML document. Use {tech_name} technology.
Requirements: {state.to_prompt()}

{context}

IMPORTANT: 
- Output a FULL HTML document with <!DOCTYPE>, <html>, <head>, <body>
- Follow the rules above
- Use examples as reference for STYLE only, adapt to requirements
- NO jQuery, use pure CSS/JS
- Animation should run automatically
- NO explanations, JUST the complete HTML code
"""

        log_step(f"🤖 Промпт разработчику (с примерами)")

        dev_task = Task(
            description=dev_prompt,
            agent=developer,
            expected_output="<!DOCTYPE html>..."
        )

        dev_crew = Crew(agents=[developer], tasks=[dev_task], verbose=False, cache=False)
        result = dev_crew.kickoff()
        result_text = result.raw if hasattr(result, 'raw') else str(result)

        # ===== REVIEWER with FEEDBACK LOOP =====
        from agents.reviewer import create_reviewer
        reviewer = create_reviewer()

        MAX_RETRIES = 2
        current_code = result_text

        for attempt in range(MAX_RETRIES + 1):
            log_step(f"🔍 Проверка кода (попытка {attempt + 1}/{MAX_RETRIES + 1})...")

            review_task = Task(
                description=f"""Review this HTML code against requirements:

        REQUIREMENTS:
        {state.to_prompt()}

        CODE:
        {current_code}

        If perfect, say "APPROVED"
        If issues found, OUTPUT THE FIXED CODE.
        """,
                agent=reviewer,
                expected_output="APPROVED or fixed code",
            )

            review_crew = Crew(agents=[reviewer], tasks=[review_task], verbose=False)
            review = review_crew.kickoff()
            review_text = review.raw if hasattr(review, 'raw') else str(review)

            if "APPROVED" in review_text.upper():
                log_step("✅ Код одобрен ревьюером")
                result_text = current_code
                break
            else:
                log_step(f"🔄 Код требует доработки, исправляю...")
                current_code = review_text  # Reviewer вернул исправленный код

                if attempt == MAX_RETRIES:
                    log_step("⚠️ Достигнут лимит попыток, использую последнюю версию")
                    result_text = current_code

        # ===== СОХРАНЕНИЕ =====
        html_file, project_dir = save_result(result_text, task_temp_dir, task_timestamp)

        log_step(f"✅ HTML: {html_file}")
        log_step(f"✅ Проект: {project_dir}")

        return result_text

    except Exception as e:
        log_step(f"❌ Ошибка: {str(e)}")
        import traceback
        log_step(f"📝 Детали: {traceback.format_exc()}")
        raise e


if __name__ == "__main__":
    test_task = "Создай страницу с черным фоном и белой линией, которая медленно растет"
    result = run_crew(test_task)
    print(f"\nРезультат:\n{result[:200]}")