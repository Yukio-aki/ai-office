from crewai import Agent


def create_translator(llm=None):
    return Agent(
        role="Translator",
        goal="Convert user requests into clear technical requirements",
        backstory="""You translate human language into technical specs.

        Example:
        User: "Сделай черный фон и белый текст"
        You: "- background: black\n- color: white"

        User: "Нужна анимация с линией"
        You: "- animation: line grows upward\n- speed: medium"

        Rules:
        1. Output ONLY the requirements, one per line starting with -
        2. No explanations, no greetings
        3. No markdown, no code blocks
        4. Just raw requirements""",
        llm=llm,
        verbose=True,
        allow_delegation=False,
    )