
import os
from dotenv import load_dotenv
from crewai import Agent, Task, Crew

# Load the .env file
load_dotenv()

api_key = os.getenv("OPENAI_API_KEY")
model_name = os.getenv("MODEL", "openai/gpt-4o-mini")

if not api_key or api_key == "your_actual_api_key_here":
    raise ValueError(
        "Please add your actual OpenAI API key to the .env file."
    )

# Ask the user for a city
city = input("Which city would you like to explore? ").strip()

if not city:
    raise ValueError("Please enter a city name.")

# Create the Travel Planner agent
planner = Agent(
    role="Travel Planner",
    goal=(
        "Recommend exactly three interesting places to visit "
        "in the city selected by the user."
    ),
    backstory=(
        "You are an experienced travel planner who helps first-time "
        "visitors discover local attractions. Your audience wants "
        "short, practical travel recommendations rather than a "
        "long travel essay."
    ),
    llm=model_name,
    verbose=True
)

# Create one task
task = Task(
    description=(
        "Recommend exactly 3 places to visit in {city}. "
        "For each place, provide the attraction name, a short "
        "description, and one practical visiting tip."
    ),
    expected_output=(
        "Exactly 3 numbered recommendations. Each recommendation "
        "must include the place name, a concise description, "
        "and one practical visiting tip. No introduction or conclusion."
    ),
    agent=planner
)

# Create the crew
crew = Crew(
    agents=[planner],
    tasks=[task],
    verbose=True
)

# Execute the crew
result = crew.kickoff(inputs={"city": city})

# Print the result
print("\n===== TRAVEL PLANNER RESULTS =====\n")
print(result)
