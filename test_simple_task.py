import os
from crewai import Agent, Task, Crew, Process

# Устанавливаем переменные окружения для Ollama
os.environ["OPENAI_API_KEY"] = "ollama"
os.environ["OPENAI_API_BASE"] = "http://localhost:11434/v1"
os.environ["OPENAI_MODEL_NAME"] = "llama2"

agent = Agent(
    role="Tester",
    goal="Say hello",
    backstory="You are a test agent",
    verbose=True,
    allow_delegation=False,
    # Не передаём llm параметр - используем переменные окружения
)

task = Task(
    description="Just say 'Hello, I am working with Ollama'",
    agent=agent,
    expected_output="A greeting message",
)

crew = Crew(
    agents=[agent],
    tasks=[task],
    verbose=True,
    process=Process.sequential,
)

print("Запускаю тест через переменные окружения...")
result = crew.kickoff()
print("Результат:", result)