from crewai import Agent

def create_reviewer(llm_config):
    return Agent(
        role="Reviewer",
        goal="Find bugs and improve code quality",
        backstory="You are a strict code reviewer.",
        llm_config=llm_config,
        verbose=True,
        allow_delegation=False,
    )