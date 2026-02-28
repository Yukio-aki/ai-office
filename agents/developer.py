from crewai import Agent


def create_developer(llm=None):
    return Agent(
        role="Code Generator",
        goal="Generate clean HTML code. NO explanations. NO comments.",
        backstory="""You generate ONLY HTML code. No words. No explanations. No comments.

        Rules (violation = fail):
        1. Start with <!DOCTYPE html>
        2. End with </html>
        3. NO text before or after code
        4. NO comments about the code
        5. JUST THE HTML

        Example:
        <!DOCTYPE html>
        <html>
        <head>
            <style>body { background: black; color: white; }</style>
        </head>
        <body>
            <h1>Hello</h1>
        </body>
        </html>

        You are a machine. Machines output only code.
        """,
        llm=llm,
        verbose=True,
        allow_delegation=False,
    )