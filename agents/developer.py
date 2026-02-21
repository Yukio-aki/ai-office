from crewai import Agent

def create_developer(llm_config):
    return Agent(
        role="Developer",
        goal="Write clean working Python code",
        backstory="You are an experienced Python developer.",
        llm_config=llm_config,  # Передаём объект LLM
        verbose=True,
        allow_delegation=False,
    )