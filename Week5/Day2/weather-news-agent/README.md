# 🌦️ AutoGen Weather News Agent

Week 5 · Day 2 assignment. An AutoGen `AssistantAgent` takes a city, calls a
DuckDuckGo news-search tool (`ddgs`, free, no key), and replies in 3 short lines.

Two ways to run it:

| File | What it is |
|---|---|
| `weather_news.py` | Terminal version (the required assignment file) |
| `app.py` | Web GUI (Streamlit) on `http://localhost:8501`, reusing the same tool |

## Setup

```bash
python -m venv .venv
# Windows:  .venv\Scripts\activate
# Mac/Linux: source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # Windows: copy .env.example .env
# then open .env and paste your OpenAI key
```

## Run

```bash
python weather_news.py      # terminal
streamlit run app.py        # browser GUI
```

## How it works

1. `search_weather_news(city: str) -> str` is a plain Python function. AutoGen reads its
   name, type hints and docstring to decide when to call it.
2. The agent gets it via `tools=[search_weather_news]`.
3. `reflect_on_tool_use=True` makes the model read the search results and write a
   3-line answer. With it off, the agent's final message is the raw tool output.

## Notes

- Only the OpenAI call needs an API key; search is keyless.
- `.env` is git-ignored so your key never reaches GitHub.
