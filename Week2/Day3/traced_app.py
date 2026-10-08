from langsmith import Client
from dotenv import load_dotenv
load_dotenv()

from langchain_openai import ChatOpenAI

llm = ChatOpenAI(model="gpt-4o-mini")

prompts = [
    "Explain digital marketing automation in simple terms.",
    "Give me 5 benefits of using AI in marketing.",
    "Explain how AI agents can automate CRM and sales activities."
]

for i, p in enumerate(prompts, start=1):
    response = llm.invoke(p)

    print(f"\n--- Run {i} ---")
    print(response.content)