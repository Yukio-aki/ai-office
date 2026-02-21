import os
from dotenv import load_dotenv
from crewai import Crew, Task, LLM

from agents.planner import create_planner
from agents.developer import create_developer
from agents.reviewer import create_reviewer

load_dotenv()

llm = LLM(
    model="deepseek-chat",
    base_url="https://api.deepseek.com",
    api_key=os.getenv("OPENAI_API_KEY"),
)

def run_crew(user_task: str):
    planner = create_planner(llm)
    developer = create_developer(llm)
    reviewer = create_reviewer(llm)

    plan_task = Task(
        description=f"Break down the task: {user_task}",
        agent=planner,
    )

    dev_task = Task(
        description="Implement the solution in Python",
        agent=developer,
    )

    review_task = Task(
        description="Review the solution and suggest fixes",
        agent=reviewer,
    )

    crew = Crew(
        agents=[planner, developer, reviewer],
        tasks=[plan_task, dev_task, review_task],
        verbose=True,
    )

    result = crew.kickoff()
    return result