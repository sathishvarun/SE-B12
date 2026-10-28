# 🌦️ AutoGen Weather News Agent

**Week 5 · Day 2 — learn. build. operate.**

An AI agent built with **Microsoft AutoGen** that takes a city name, calls a
search tool, and replies with today's weather in **exactly 3 short lines**.
It runs in the terminal and also has a clean web interface built with **Streamlit**.

---

## ✨ What it does

1. You type a city (e.g. `Chennai`).
2. The agent decides to call its tool `search_weather_news(city)`.
3. The tool collects:
   - **Live weather data** from [wttr.in](https://wttr.in) (free, no API key)
   - **Weather news headlines** from DuckDuckGo via the `ddgs` package (free, no API key)
4. With `reflect_on_tool_use=True`, the model reads those results and writes
   a short 3-line weather report instead of dumping raw search output.

---

## 🧠 Key concepts

| Concept | How it is used |
|---|---|
| **AutoGen AssistantAgent** | The agent that reasons, calls tools and writes the answer |
| **Tool calling** | A plain Python function passed via `tools=[...]` |
| **Docstring as instructions** | The agent reads the function name, type hints and docstring to decide *when* to call the tool |
| **reflect_on_tool_use** | Makes the model summarise tool results instead of returning them raw |
| **Async streaming** | `agent.run_stream()` + `Console` show each step (tool call → result → answer) |
| **Relevance filtering** | Only headlines whose title is about weather *and* mention the city are kept |
| **Secrets management** | API key lives in `.env` (git-ignored), loaded with `python-dotenv` |

---

## 🗂️ Project structure

```
weather-news-agent/
├── weather_news.py        # Terminal version (main assignment file)
├── app.py                 # Streamlit web GUI (reuses the same tool)
├── requirements.txt       # Python packages
├── .env.example           # Template for your API key
├── .gitignore             # Keeps .env and .venv out of GitHub
└── .streamlit/config.toml # GUI theme
```

---

## ⚙️ Setup (Mac)

```bash
# 1. Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 2. Install packages
pip install -r requirements.txt

# 3. Add your OpenAI key
cp .env.example .env
# open .env and replace sk-your-key-here with your real key
```

> Windows: use `python -m venv .venv`, `.venv\Scripts\activate` and `copy .env.example .env`.
> If you use Anaconda, run `conda deactivate` first.

---

## ▶️ Run

**Terminal version**
```bash
python weather_news.py
```

**Web GUI (localhost)**
```bash
python -m streamlit run app.py
```
Opens at **http://localhost:8501**: pick a city, read the 3-line report,
and open **🔧 Agent trace** to see the tool call and raw results.

---

## 💬 Example

**Input**
```
Which city? Chennai
```

**Output (terminal)**
```
---------- ToolCallRequestEvent (weather_news) ----------
[FunctionCall(name='search_weather_news', arguments='{"city":"Chennai"}')]
---------- ToolCallExecutionEvent (weather_news) ----------
LIVE WEATHER DATA (wttr.in): ...  WEATHER NEWS HEADLINES (DuckDuckGo): ...
---------- TextMessage (weather_news) ----------
Chennai is partly cloudy today with humid conditions.
Around 29°C now, high of 31°C, with a 60% chance of rain.
Carry an umbrella for evening showers.
```
*(Actual values change daily.)*

---

## 🔍 Why `reflect_on_tool_use=True`?

Without it, the agent's final message is the **raw tool output**: a long block
of numbers and headlines. With it, the model reads the results and writes a
short, human-friendly answer.

---

## 🛠️ Tech stack

Python · AutoGen (`autogen-agentchat`, `autogen-ext[openai]`) · OpenAI `gpt-4.1-mini` ·
`ddgs` (DuckDuckGo search) · wttr.in · Streamlit · python-dotenv

---

## 🔐 Security

- `.env` is listed in `.gitignore`, so the API key never reaches GitHub.
- Only `.env.example` (with a placeholder) is committed.

---

## 👤 Author

**Sathish Varun**, Week 5 · Day 2 assignment ([socialeagle.ai](https://socialeagle.ai))
