import os
import re
from crewai import Agent, Task, Crew
from datetime import datetime
import json


class LLMExtractor:
    """Использует LLM для извлечения требований из текста"""

    def __init__(self):
        self.extractor_agent = Agent(
            role="Requirement Extractor",
            goal="Extract structured requirements from user messages",
            backstory="""You are an expert at understanding user requests and 
            converting them into structured, technical requirements. You NEVER 
            add your own opinions, just extract what the user said.""",
            verbose=False,
            allow_delegation=False,
        )

    def extract(self, user_message: str, current_requirements: dict = None) -> dict:
        """Извлекает требования из сообщения пользователя"""

        # Формируем контекст
        context = ""
        if current_requirements:
            context = f"\nCurrent requirements (update these based on new message):\n{json.dumps(current_requirements, indent=2, ensure_ascii=False)}"

        extract_task = Task(
            description=f"""
            EXTRACT STRUCTURED REQUIREMENTS. RETURN ONLY JSON. NO OTHER TEXT.

            User message: "{user_message}"
            {context}

            You MUST return a valid JSON object with exactly these fields:
            {{
                "project_type": null or "website"|"parser"|"bot"|"script"|"animation",
                "technologies": [],
                "forbidden": [],
                "colors": [],
                "style": null or "abstract"|"geometric"|"organic"|"minimal"|"dark",
                "animation_speed": null or "slow"|"medium"|"fast",
                "features": [],
                "mood": null or "dark"|"light"|"mysterious",
                "has_examples": false,
                "confidence": 0.0,
                "missing_info": []
            }}

            RULES (VIOLATION = TASK FAILED):
            1. Return ONLY the JSON object
            2. No explanations before or after
            3. No "Here is your JSON"
            4. No markdown formatting
            5. Just raw JSON starting with {{ and ending with }}

            YOUR RESPONSE MUST BE ONLY THE JSON:
            """,
            agent=self.extractor_agent,
            expected_output="JSON object",
        )

        crew = Crew(
            agents=[self.extractor_agent],
            tasks=[extract_task],
            verbose=False
        )

        result = crew.kickoff()

        # Получаем строковый результат
        result_str = ""
        if hasattr(result, 'raw'):
            result_str = result.raw
        else:
            result_str = str(result)

        # Пытаемся извлечь JSON из строки
        try:
            # Ищем JSON в ответе
            json_match = re.search(r'\{.*\}', result_str, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            else:
                # Если нет JSON, пробуем распарсить всю строку
                return json.loads(result_str)
        except Exception as e:
            print(f"Failed to parse JSON: {e}")
            print(f"Raw response: {result_str[:200]}")
            # Возвращаем пустой словарь
            return {
                "project_type": None,
                "technologies": [],
                "forbidden": [],
                "colors": [],
                "style": None,
                "animation_speed": None,
                "features": [],
                "mood": None,
                "has_examples": False,
                "confidence": 0.1,
                "missing_info": ["Could not parse requirements"]
            }