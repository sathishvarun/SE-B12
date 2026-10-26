"""
Week 5 · Day 1 — AutoGen HR Assistant Agent (terminal version)

An AssistantAgent with the system message "You are an HR assistant."
writes a 5-line job description for a Junior Python Developer.

All settings (API key, model, job title) are loaded from the .env file.

Run in the terminal:
    python hr_agent.py

For the browser (localhost) version, run:
    python app.py
"""

import asyncio
import os
import sys

from dotenv import load_dotenv
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.ui import Console
from autogen_ext.models.openai import OpenAIChatCompletionClient

# ---------------------------------------------------------------------------
# 1. Load settings from the .env file
# ---------------------------------------------------------------------------
load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
MODEL_NAME = os.getenv("OPENAI_MODEL", "gpt-4o-mini").strip() or "gpt-4o-mini"
JOB_TITLE = os.getenv("JOB_TITLE", "Junior Python Developer").strip() or "Junior Python Developer"

# ---------------------------------------------------------------------------
# 2. Agent details (who the agent is and what it is responsible for)
# ---------------------------------------------------------------------------
AGENT_NAME = "hr_assistant"
SYSTEM_MESSAGE = "You are an HR assistant."  # required exactly by the assignment


def build_responsibility(job_title: str) -> str:
    """One-line description of what the agent is asked to do."""
    return f"Write a 5-line job description for a {job_title}."


def build_task(job_title: str) -> str:
    """The task text. "5 lines" is defined clearly so the model doesn't guess."""
    return (
        f"Write a job description for a {job_title}.\n"
        "Format rules:\n"
        f"- First line: the title '{job_title}' only.\n"
        "- Then exactly 5 numbered lines (1. to 5.), one short sentence each:\n"
        "  1. Role summary\n"
        "  2. Key responsibilities\n"
        "  3. Required skills\n"
        "  4. Tools and technologies\n"
        "  5. Growth and learning opportunities\n"
        "- Do not add the labels above, an intro, closing remarks, extra lines, "
        "or markdown bold/headings."
    )


def api_key_is_set(key: str) -> bool:
    """True when a real-looking key is present (not empty, not the placeholder)."""
    return bool(key) and not key.startswith("your-")


def print_agent_info() -> None:
    """Show the setup details before the agent runs."""
    print("=" * 60)
    print(" AutoGen HR Assistant Agent")
    print("=" * 60)
    print(f" Model          : {MODEL_NAME}")
    print(f" Agent name     : {AGENT_NAME}")
    print(f" Agent role     : {SYSTEM_MESSAGE}")
    print(f" Responsibility : {build_responsibility(JOB_TITLE)}")
    print(f" Job title      : {JOB_TITLE}")
    print(" Output format  : Title + exactly 5 numbered lines")
    print("=" * 60)


async def main() -> None:
    # Stop early with a clear message if the key is missing.
    if not api_key_is_set(OPENAI_API_KEY):
        sys.exit("ERROR: OPENAI_API_KEY is missing. Add it to your .env file.")

    print_agent_info()

    # Model client — connects the agent to OpenAI.
    model_client = OpenAIChatCompletionClient(model=MODEL_NAME, api_key=OPENAI_API_KEY)

    # The agent — its behaviour is set by the system message.
    agent = AssistantAgent(
        name=AGENT_NAME,
        model_client=model_client,
        system_message=SYSTEM_MESSAGE,
    )

    try:
        # Run the task and stream the reply to the terminal.
        await Console(agent.run_stream(task=build_task(JOB_TITLE)))
    finally:
        # Always close the client, otherwise the script can hang.
        await model_client.close()


if __name__ == "__main__":
    asyncio.run(main())
