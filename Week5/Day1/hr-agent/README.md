# AutoGen HR Assistant Agent

Week 5 · Day 1 assignment: my first AutoGen agent.

An `AssistantAgent` with the system message **"You are an HR assistant."** writes a 5-line job description for a Junior Python Developer. It runs two ways:

- **Browser (localhost):** `python app.py` opens http://127.0.0.1:8000
- **Terminal:** `python hr_agent.py` prints the reply with AutoGen's `Console`

The OpenAI API key and settings are loaded from a `.env` file.

## Agent details

| Item | Value |
|---|---|
| Framework | AutoGen (autogen-agentchat + autogen-ext) |
| Model | `gpt-4o-mini` (change in `.env` or in the page) |
| Agent name | `hr_assistant` |
| Role (system message) | You are an HR assistant. |
| Responsibility | Write a 5-line job description for a Junior Python Developer |
| Output format | Title + exactly 5 numbered lines |
| Web server | FastAPI + Uvicorn on 127.0.0.1:8000 |

## Project structure

```
hr-agent/
├── app.py             # localhost web app (FastAPI)
├── hr_agent.py        # terminal version + shared agent logic
├── static/
│   └── index.html     # the browser page
├── .env.example       # template for .env
├── .env               # your real API key (you create it; NOT pushed to GitHub)
├── requirements.txt   # Python packages
├── start.bat          # one-click start (Windows)
├── start.sh           # one-click start (macOS / Linux)
├── .gitignore         # keeps .env and venv out of Git
└── README.md
```

## Quick start (Windows)

1. Extract the zip.
2. Double-click `start.bat`. The first time, it installs everything and opens `.env` in Notepad.
3. Paste your key after `OPENAI_API_KEY=`, save, and close Notepad.
4. Double-click `start.bat` again. The browser opens at http://127.0.0.1:8000.

## Manual start

```bash
python -m venv venv
venv\Scripts\Activate.ps1        # Windows PowerShell
# source venv/bin/activate       # macOS / Linux

pip install -r requirements.txt

copy .env.example .env           # Windows
# cp .env.example .env           # macOS / Linux
# then edit .env and paste your key

python app.py                    # browser version
python hr_agent.py               # terminal version
```

Stop the web server with **CTRL+C**.

## Key points

- **Async:** AutoGen runs on asyncio. The terminal script uses `asyncio.run(main())`; the web app uses async FastAPI endpoints.
- **"5 lines" made explicit:** the task asks for a title plus exactly 5 numbered, one-sentence lines.
- **System message matters:** pick Recruiter or Lawyer in the page and the same request gives a different tone.
- **Clean shutdown:** `model_client.close()` runs in a `finally` block after every run.
- **No secrets in code:** the API key comes from `.env`, which is ignored by Git.
