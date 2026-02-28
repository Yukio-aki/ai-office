import os
from crewai import Agent, Task, Crew

# Настройки модели
os.environ["OPENAI_API_KEY"] = "ollama"
os.environ["OPENAI_API_BASE"] = "http://localhost:11434/v1"
os.environ["OPENAI_MODEL_NAME"] = "tinyllama"

print("=" * 60)
print("🚀 ТЕСТ: ПРЯМОЙ ЗАПРОС К МОДЕЛИ")
print("=" * 60)

# Создаем агента
agent = Agent(
    role="HTML Writer",
    goal="Write HTML code",
    backstory="You write HTML code. Output only the code.",
    verbose=True,
)

# Простой запрос
task = Task(
    description="Напиши HTML с черным фоном и белым текстом",
    agent=agent,
    expected_output="<!DOCTYPE html>...",
)

# Запускаем
crew = Crew(agents=[agent], tasks=[task], verbose=False, cache=False)
result = crew.kickoff()

# Выводим результат
result_text = result.raw if hasattr(result, 'raw') else str(result)
print("\n" + "=" * 60)
print("✅ РЕЗУЛЬТАТ:")
print("=" * 60)
print(result_text)

# Сохраняем в файл
with open("test_result.html", "w", encoding='utf-8') as f:
    f.write(result_text)
print("\n✅ Результат сохранен в test_result.html")