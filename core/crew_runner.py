import os
from dotenv import load_dotenv
from crewai import Crew, Task, Process
from crewai import Agent

# ВАЖНО: используем LiteLLM напрямую
import litellm
from litellm import completion

# Настраиваем LiteLLM для Ollama
litellm.set_verbose = True

from agents.planner import create_planner
from agents.developer import create_developer
from agents.reviewer import create_reviewer

load_dotenv()


# Создаем кастомный класс для совместимости с CrewAI
class OllamaLLM:
    def __init__(self, model="ollama/llama2", base_url="http://localhost:11434"):
        self.model = model
        self.base_url = base_url

    def generate(self, prompt, **kwargs):
        response = completion(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            api_base=self.base_url,
            **kwargs
        )
        return response.choices[0].message.content

    def __call__(self, prompt, **kwargs):
        return self.generate(prompt, **kwargs)


# Создаем экземпляр LLM для Ollama
llm = OllamaLLM(model="ollama/llama2", base_url="http://localhost:11434")


def run_crew(user_task: str):
    planner = create_planner(llm)
    developer = create_developer(llm)
    reviewer = create_reviewer(llm)

    # Задача 1: Планировщик
    plan_task = Task(
        description=f"""
        Проанализируй задачу пользователя и разбей её на чёткие шаги.
        Задача: {user_task}

        Твой ответ должен содержать:
        1. Понимание задачи
        2. Список конкретных шагов для разработчика
        3. Требования к коду
        """,
        agent=planner,
        expected_output="Детальный план реализации с пошаговыми инструкциями",
    )

    # Задача 2: Разработчик
    dev_task = Task(
        description=f"""
        Напиши чистый рабочий Python код на основе плана.

        План от планировщика:
        {{plan_task.output}}

        Требования:
        - Код должен быть готов к запуску
        - Добавь комментарии
        - Обработай возможные ошибки
        """,
        agent=developer,
        expected_output="Рабочий Python код с комментариями",
        context=[plan_task],
    )

    # Задача 3: Ревьюер
    review_task = Task(
        description=f"""
        Проверь код и найди проблемы.

        Код для проверки:
        {{dev_task.output}}

        Что проверить:
        1. Синтаксические ошибки
        2. Логические ошибки
        3. Стиль кода (PEP8)
        4. Предложения по улучшению

        Дай финальную версию кода с исправлениями.
        """,
        agent=reviewer,
        expected_output="Исправленный код с комментариями ревью",
        context=[dev_task],
    )

    crew = Crew(
        agents=[planner, developer, reviewer],
        tasks=[plan_task, dev_task, review_task],
        process=Process.sequential,
        verbose=True,
    )

    result = crew.kickoff()
    return result