import os
from crewai import Agent, Task, Crew
from agents.clarifier import create_clarifier

os.environ["OPENAI_API_KEY"] = "ollama"
os.environ["OPENAI_API_BASE"] = "http://localhost:11434/v1"
os.environ["OPENAI_MODEL_NAME"] = "phi3:mini"

clarifier = create_clarifier()

test_requests = [
    "Сделай красивую анимацию",
    "Черный фон с белой линией",
    "Черный фон и белая линия которая медленно растет"
]

for req in test_requests:
    print("\n" + "=" * 60)
    print(f"👤 Запрос: {req}")

    task = Task(
        description=f"Analyze this request and ask questions if needed: {req}",
        agent=clarifier,
        expected_output="QUESTIONS: ... or NO_QUESTIONS"
    )

    crew = Crew(agents=[clarifier], tasks=[task], verbose=False)
    result = crew.kickoff()

    print(f"🤖 Ответ: {result.raw if hasattr(result, 'raw') else result}")