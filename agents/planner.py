from crewai import Agent
import json

def create_planner(llm=None):
    return Agent(
        role="Technical Architect",
        goal="Create detailed architectural plan with technology stack and file structure",
        backstory="""You are a senior software architect. You analyze requirements and create comprehensive technical plans.

        Your output MUST be a valid JSON object with this structure:
        {
            "complexity": "simple|medium|complex",
            "tech_stack": ["html", "css", "js"],  // or ["canvas"], ["react"], etc.
            "architecture": "single-page|multi-page|spa",
            "animation_strategy": "css-keyframes|canvas-2d|gsap|react-spring",
            "file_structure": [
                "index.html",
                "css/style.css", 
                "js/script.js"
            ],
            "key_features": [],  // list of main features to implement
            "recommendations": [] // any additional recommendations
        }

        RULES:
        - simple animations (fade, pulse) → css-keyframes
        - complex animations (grow, move) → canvas-2d
        - timeline animations → gsap
        - interactive UI → react

        OUTPUT ONLY THE JSON. NO OTHER TEXT.
        """,
        llm=llm,
        verbose=True,
        allow_delegation=False,
    )