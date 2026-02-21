from crewai import Agent

def create_planner(llm_config):
    return Agent(
        role="Planner",
        goal="Break down user tasks into clear steps",
        backstory="You are a senior project planner.",
        llm_config=llm_config,
        verbose=True,
        allow_delegation=False,
    )