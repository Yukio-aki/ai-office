from crewai import Agent

def create_developer(llm):
    return Agent(
        role="Developer",
        goal="Write clean working Python code",
        backstory="You are an experienced Python developer.",
        llm=llm,
        verbose=True,
        allow_delegation=False,
    )