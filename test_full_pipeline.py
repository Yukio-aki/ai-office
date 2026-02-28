import os
import sys
from pathlib import Path

# Добавляем путь к проекту
sys.path.append(str(Path(__file__).parent))

from core.crew_runner import run_crew
from agents.clarifier import create_clarifier
from core.clarifier_loop import ClarifierLoop
from crewai import Task, Crew

os.environ["OPENAI_API_KEY"] = "ollama"
os.environ["OPENAI_API_BASE"] = "http://localhost:11434/v1"
os.environ["OPENAI_MODEL_NAME"] = "phi3:mini"


def run_with_clarifier(initial_task: str):
    """Запускает пайплайн с уточнением вопросов"""

    print("\n" + "=" * 60)
    print("🚀 ЗАПУСК С CLARIFIER")
    print("=" * 60)

    print(f"\n👤 Исходный запрос: {initial_task}")

    # ===== CLARIFIER =====
    clarifier = create_clarifier()
    clarifier_loop = ClarifierLoop()

    task = Task(
        description=f"Analyze this request and ask questions if needed: {initial_task}",
        agent=clarifier,
        expected_output="QUESTIONS: ... or NO_QUESTIONS"
    )

    crew = Crew(agents=[clarifier], tasks=[task], verbose=False)
    result = crew.kickoff()
    output = result.raw if hasattr(result, 'raw') else str(result)

    # ===== ОТЛАДКА =====
    print("\n🔍 RAW ответ Clarifier:")
    print(output)
    print("-" * 60)
    # ===================

    # Проверяем, есть ли вопросы
    clarifier_loop.set_questions(output)

    # Проверяем, есть ли вопросы
    clarifier_loop.set_questions(output)

    if clarifier_loop.needs_clarification:
        print("\n🤖 Уточняющие вопросы:")

        # Задаем вопросы и собираем ответы
        while not clarifier_loop.is_finished():
            question = clarifier_loop.get_next_question()
            print(f"\n❓ {question}")

            # Собираем многострочный ответ
            print("👉 Ваш ответ (для завершения нажмите Enter дважды):")
            lines = []
            while True:
                line = input()
                if line == "":
                    break
                lines.append(line)

            answer = " ".join(lines) if lines else input("👉 Ваш ответ (одной строкой): ")
            clarifier_loop.add_answer(answer)

        # Формируем уточненный запрос
        refined_task = initial_task + "\n" + clarifier_loop.get_all_answers()
        print(f"\n📋 Уточненный запрос: {refined_task[:100]}...")
    else:
        print("\n✅ Вопросов нет, использую исходный запрос")
        refined_task = initial_task

    # ===== ОСНОВНОЙ ПАЙПЛАЙН =====
    print("\n" + "=" * 60)
    print("🚀 ЗАПУСК ОСНОВНОГО ПАЙПЛАЙНА")
    print("=" * 60)

    result = run_crew(refined_task)

    print("\n" + "=" * 60)
    print("✅ РЕЗУЛЬТАТ:")
    print("=" * 60)
    print(result[:500] + "..." if len(result) > 500 else result)

    return result


if __name__ == "__main__":
    # Тестовые запросы
    test_requests = [
        "Сделай красивую анимацию",
        "Черный фон с белой линией",
        "Черный фон и белая линия которая медленно растет",
        "Свой вариант"
    ]

    print("Выберите запрос:")
    for i, req in enumerate(test_requests):
        print(f"{i + 1}. {req}")

    choice = input("\nВаш выбор (1-4): ").strip()

    if choice == "4":
        user_task = input("Введите ваш запрос: ")
    elif choice in ["1", "2", "3"]:
        user_task = test_requests[int(choice) - 1]
    else:
        print("❌ Неверный выбор, использую тестовый запрос")
        user_task = test_requests[0]

    run_with_clarifier(user_task)