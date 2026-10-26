"""
Week 5 · Day 1 — AutoGen HR Assistant Agent (localhost web version)

Starts a local web server and opens the app in your browser:
    python app.py
    -> http://127.0.0.1:8000

The same AutoGen AssistantAgent runs behind the page. The API key and
default settings are read from the .env file (re-read on every request,
so you can edit .env without restarting).
"""

import os
import threading
import webbrowser
from pathlib import Path

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field

from autogen_agentchat.agents import AssistantAgent
from autogen_ext.models.openai import OpenAIChatCompletionClient

from hr_agent import AGENT_NAME, api_key_is_set, build_responsibility, build_task

BASE_DIR = Path(__file__).resolve().parent
HOST = "127.0.0.1"
PORT = int(os.getenv("PORT", "8000"))

# Roles you can pick in the page. "hr" is the assignment's required role;
# the others are for the "swap the system message" experiment.
ROLES = {
    "hr": "You are an HR assistant.",
    "recruiter": "You are a recruiter.",
    "lawyer": "You are a lawyer.",
}

MODELS = ["gpt-4o-mini", "gpt-4o", "gpt-4.1-mini", "gpt-4.1"]

app = FastAPI(title="AutoGen HR Assistant Agent")


class GenerateRequest(BaseModel):
    job_title: str = Field(default="Junior Python Developer", max_length=80)
    role: str = "hr"
    model: str = ""


def load_settings() -> dict:
    """Read .env fresh each time so edits apply without a restart."""
    load_dotenv(BASE_DIR / ".env", override=True)
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini").strip() or "gpt-4o-mini"
    return {
        "api_key": os.getenv("OPENAI_API_KEY", "").strip(),
        "model": model,
        "job_title": os.getenv("JOB_TITLE", "Junior Python Developer").strip()
        or "Junior Python Developer",
    }


def friendly_error(exc: Exception) -> str:
    """Turn OpenAI / network errors into plain-English messages."""
    name = type(exc).__name__
    text = str(exc)
    if name == "AuthenticationError" or "401" in text:
        return "Your OpenAI API key is not valid. Check OPENAI_API_KEY in the .env file."
    if name == "RateLimitError" or "insufficient_quota" in text or "429" in text:
        return "OpenAI quota or rate limit reached. Add billing credit or wait a minute."
    if name == "NotFoundError" or "model_not_found" in text:
        return "That model is not available on your OpenAI account. Pick gpt-4o-mini."
    if name in ("APIConnectionError", "APITimeoutError"):
        return "Could not reach OpenAI. Check your internet connection."
    return f"{name}: {text}"


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(BASE_DIR / "static" / "index.html")


@app.get("/api/info")
async def info() -> dict:
    s = load_settings()
    models = MODELS if s["model"] in MODELS else [s["model"], *MODELS]
    return {
        "agent_name": AGENT_NAME,
        "default_model": s["model"],
        "default_job_title": s["job_title"],
        "models": models,
        "roles": ROLES,
        "api_key_configured": api_key_is_set(s["api_key"]),
    }


@app.post("/api/generate")
async def generate(req: GenerateRequest):
    s = load_settings()
    if not api_key_is_set(s["api_key"]):
        return JSONResponse(
            status_code=400,
            content={"error": "OPENAI_API_KEY is missing. Add it to the .env file, save, and try again."},
        )

    job_title = req.job_title.strip() or s["job_title"]
    system_message = ROLES.get(req.role, ROLES["hr"])
    model = req.model.strip() or s["model"]

    model_client = OpenAIChatCompletionClient(model=model, api_key=s["api_key"])
    agent = AssistantAgent(
        name=AGENT_NAME,
        model_client=model_client,
        system_message=system_message,
    )

    try:
        result = await agent.run(task=build_task(job_title))
        output = str(result.messages[-1].content).strip()
        usage = result.messages[-1].models_usage
    except Exception as exc:  # report any OpenAI/network error to the page
        return JSONResponse(status_code=502, content={"error": friendly_error(exc)})
    finally:
        # Always close the client so connections are not left open.
        await model_client.close()

    # Also log to the terminal so you can see it there too.
    print(f"\n---------- TextMessage ({AGENT_NAME}) ----------\n{output}\n")

    return {
        "model": model,
        "agent_name": AGENT_NAME,
        "system_message": system_message,
        "responsibility": build_responsibility(job_title),
        "job_title": job_title,
        "output": output,
        "tokens": (usage.prompt_tokens + usage.completion_tokens) if usage else None,
    }


def open_browser() -> None:
    webbrowser.open(f"http://{HOST}:{PORT}")


if __name__ == "__main__":
    print("=" * 60)
    print(" AutoGen HR Assistant Agent — localhost")
    print(f" Open in your browser: http://{HOST}:{PORT}")
    print(" Press CTRL+C to stop the server.")
    print("=" * 60)
    if os.getenv("NO_BROWSER") != "1":
        threading.Timer(1.5, open_browser).start()
    uvicorn.run(app, host=HOST, port=PORT, log_level="warning")
