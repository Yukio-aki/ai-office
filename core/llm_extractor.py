import os
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
            Extract structured requirements from this user message:

            "{user_message}"
            {context}

            Return ONLY a JSON object with these fields (use null if not mentioned):
            {{
                "project_type": null or "website"|"parser"|"bot"|"script"|"animation",
                "technologies": [],  // list of mentioned technologies
                "forbidden": [],      // list of things user doesn't want
                "colors": [],         // list of colors mentioned
                "style": null or "abstract"|"geometric"|"organic"|"minimal"|"dark",
                "animation_speed": null or "slow"|"medium"|"fast",
                "features": [],       // list of specific features requested
                "mood": null or "dark"|"light"|"mysterious",
                "has_examples": false,  // whether user provided examples
                "confidence": 0.0,     // 0-1 how clear is the requirement
                "missing_info": []      // what's clearly missing
            }}

            IMPORTANT: 
            - Extract ONLY what the user explicitly said
            - Do NOT add interpretations
            - If something is unclear, note it in missing_info
            - Return ONLY the JSON, no other text
            """,
            agent=self.extractor_agent,
            expected_output="JSON object with extracted requirements",
        )

        crew = Crew(
            agents=[self.extractor_agent],
            tasks=[extract_task],
            verbose=False
        )

        result = crew.kickoff()

        try:
            # Пробуем распарсить JSON из ответа
            if hasattr(result, 'raw'):
                # Ищем JSON в ответе
                import re
                json_match = re.search(r'\{.*\}', result.raw, re.DOTALL)
                if json_match:
                    return json.loads(json_match.group())
            return json.loads(str(result))
        except:
            # Если не получилось, возвращаем пустой словарь
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