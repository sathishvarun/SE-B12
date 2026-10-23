
import os
from dotenv import load_dotenv
from crewai import Agent, Task, Crew, Process
from crewai_tools import SerperDevTool


# --------------------------------------------------
# 1. Load environment variables from .env
# --------------------------------------------------

load_dotenv()

required_keys = ["OPENAI_API_KEY", "SERPER_API_KEY", "MODEL"]

missing_keys = [
    key for key in required_keys
    if not os.getenv(key)
]

if missing_keys:
    raise ValueError(
        f"Missing environment variables: {', '.join(missing_keys)}. "
        "Please check your .env file."
    )

model_name = os.getenv("MODEL")

print("Environment variables loaded successfully.")
print(f"Using model: {model_name}")


# --------------------------------------------------
# 2. Initialize the Researcher's search tool
# --------------------------------------------------

search_tool = SerperDevTool()


# --------------------------------------------------
# 3. Create the Researcher Agent
# --------------------------------------------------

researcher = Agent(
    role="Technology News Researcher",
    goal=(
        "Find today's three most important and relevant "
        "technology news stories using current web search results."
    ),
    backstory=(
        "You are an experienced technology news researcher. "
        "You identify credible, recent stories about AI, software, "
        "cybersecurity, technology companies, and innovation. "
        "You verify dates and sources, avoid duplicate stories, "
        "and distinguish confirmed facts from speculation."
    ),
    tools=[search_tool],
    llm=model_name,
    verbose=True,
    allow_delegation=False
)


# --------------------------------------------------
# 4. Create the Writer Agent
# --------------------------------------------------

writer = Agent(
    role="Technology Newsletter Writer",
    goal=(
        "Transform the researcher's findings into a concise, "
        "accurate, reader-friendly technology newsletter."
    ),
    backstory=(
        "You are a professional technology newsletter editor. "
        "You work only with the research provided to you. "
        "You do not conduct additional research or invent facts. "
        "You write concise headlines and explain why technology "
        "developments matter to readers."
    ),
    llm=model_name,
    verbose=True,
    allow_delegation=False
)


# --------------------------------------------------
# 5. Task 1: Research today's top three tech stories
# --------------------------------------------------

find = Task(
    description=(
        "Search the web for today's top three technology news stories. "
        "Use current search results and prioritize stories published "
        "today. If fewer than three qualifying stories are available, "
        "use the most recent relevant stories and clearly state their "
        "publication dates. Do not present old news as new. "
        "Avoid duplicate stories. For each story, provide: "
        "(1) headline, (2) publication date, "
        "(3) a factual two-sentence summary, "
        "(4) publisher name, and (5) source URL. "
        "Choose three distinct, significant stories that are useful "
        "for a general technology audience."
    ),
    expected_output=(
        "A structured research brief containing exactly three numbered "
        "technology news stories. Each story must include its headline, "
        "publication date, two-sentence factual summary, publisher, "
        "and source URL. Clearly label all three stories."
    ),
    agent=researcher
)


# --------------------------------------------------
# 6. Task 2: Write the five-line newsletter
# --------------------------------------------------

write = Task(
    description=(
        "Using ONLY the research brief supplied by the Researcher, "
        "write a newsletter for today's technology news. "
        "Do not use search tools or introduce unsupported facts. "
        "Follow this exact five-line structure:\n"
        "Line 1: Tech in 5 Lines — [today's date]\n"
        "Line 2: 1. [First story in one concise line]\n"
        "Line 3: 2. [Second story in one concise line]\n"
        "Line 4: 3. [Third story in one concise line]\n"
        "Line 5: Why it matters: [one concise overall takeaway]\n"
        "Keep each story on one physical line. "
        "Do not add blank lines, introductions, conclusions, "
        "markdown code fences, or extra commentary."
    ),
    expected_output=(
        "Exactly five non-empty physical lines: one headline, "
        "three numbered technology news stories, and one "
        "'Why it matters:' takeaway. No extra lines."
    ),
    agent=writer,
    context=[find]
)


# --------------------------------------------------
# 7. Create the sequential Crew
# --------------------------------------------------

crew = Crew(
    agents=[researcher, writer],
    tasks=[find, write],
    process=Process.sequential,
    verbose=True
)


# --------------------------------------------------
# 8. Execute the Crew and validate the output
# --------------------------------------------------

if __name__ == "__main__":
    print("\nStarting the Two-Agent Tech Newsletter Crew...\n")

    result = crew.kickoff()

    newsletter = str(result.raw).strip()
    lines = newsletter.splitlines()

    print("\n" + "=" * 50)
    print("FINAL TECHNOLOGY NEWSLETTER")
    print("=" * 50)
    print(newsletter)
    print("=" * 50)

    if len(lines) == 5 and all(line.strip() for line in lines):
        print("\nSUCCESS: Newsletter contains exactly five lines.")
    else:
        print(
            f"\nVALIDATION WARNING: Expected five non-empty lines; "
            f"received {len(lines)} lines."
        )
