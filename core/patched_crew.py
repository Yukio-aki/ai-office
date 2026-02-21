import os
from crewai import Crew, Task, Process, Agent


# Модифицируем стандартный класс Crew
class PatchedCrew(Crew):
    def __init__(self, *args, **kwargs):
        # Принудительно устанавливаем модель по умолчанию
        os.environ["OPENAI_DEFAULT_MODEL"] = "ollama/llama2"
        super().__init__(*args, **kwargs)

    def kickoff(self):
        # Перед запуском проверяем конфигурацию
        for agent in self.agents:
            if hasattr(agent, 'llm_config'):
                agent.llm_config['model'] = 'ollama/llama2'
        return super().kickoff()