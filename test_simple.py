# test_direct.py
from crewai import Agent, Task, Crew

agent = Agent(
    role="HTML Writer",
    goal="Write HTML code",
    backstory="You write HTML",
    verbose=True
)

task = Task(
    description="Напиши HTML с черным фоном",
    agent=agent,
    expected_output="<!DOCTYPE html>..."
)

crew = Crew(agents=[agent], tasks=[task])
result = crew.kickoff()
print(result)