from crewai import Agent

def create_reviewer(llm):
    return Agent(
        role="Reviewer",
        goal="Find bugs and improve code quality",
        backstory="You are a strict code reviewer.",
        llm=llm,
        verbose=True,
        allow_delegation=False,
    )