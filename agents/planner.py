from crewai import Agent

def create_planner(llm):
    return Agent(
        role="Planner",
        goal="Break down user tasks into clear steps",
        backstory="You are a senior project planner.",
        llm=llm,
        verbose=True,
    )