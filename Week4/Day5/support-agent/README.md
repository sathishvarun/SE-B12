# Customer Support Agent (CrewAI + RAG) — runs on localhost

## How it answers
1. **Step 1 – Your content (RAG):** Knowledge Base Agent searches the files in `knowledge/`.
2. **Step 2 – Web:** if not found, Web Research Agent searches Google (Serper) and reads pages.
3. **Step 3 – Manual entry:** if still not found, the customer fills a form (name, email,
   phone, details). It is saved in `data/support.db` and the Escalation Agent adds a
   summary and priority. When you answer the ticket, the answer is added to the
   knowledge base, so Step 1 can answer it next time.

## Setup (Mac, one time)
```bash
cd support-agent
/opt/anaconda3/bin/python -m venv venv      # Python 3.10–3.13 only (NOT plain python3 = 3.14)
source venv/bin/activate
python --version                            # must show 3.11.x (or 3.10–3.13)
python -m pip install -r requirements.txt
cp .env.example .env
open -e .env                                # add OPENAI_API_KEY and SERPER_API_KEY, save
python ingest.py                            # index the files in knowledge/
```

Your `.env` should contain:
```
OPENAI_API_KEY=sk-...
SERPER_API_KEY=...
CREWAI_TRACING_ENABLED=false
CREWAI_DISABLE_TELEMETRY=true
```

## Run on localhost
```bash
cd ~/Downloads/SE-B12/Week4/Day5/support-agent
source venv/bin/activate
python -m streamlit run app.py
```
Open **http://localhost:8501** in your browser. Stop the server with **Ctrl + C**.

> Always use `python -m streamlit run app.py`, not plain `streamlit run app.py`.
> Plain `streamlit` can start Anaconda's old copy instead of the one in your venv.

## Pages
- **💬 Customer Chat** – ask questions; each answer shows which step answered it.
  Click **"How the agents handled this"** under an answer to see the steps that ran.
- **🎫 Tickets** – all manual entries; answer and resolve them.
- **📚 Knowledge Base** – upload PDF / TXT / MD files and re-index.

## Test questions (Google example)
Step 1 only works if your file in `knowledge/` contains Google FAQ content.

**📗 Step 1 – Your content (RAG)**
- What is Google?
- How do I recover my Google account if I forget my password?
- How do I turn on 2-Step Verification for my Google account?
- How much free storage does a Google account include?

**🌐 Step 2 – Web search**
- Who is the current CEO of Google?
- What was Alphabet's total revenue in its latest fiscal year?
- What is Alphabet's stock ticker symbol and where is it listed?
- What are the latest Google AI announcements in 2026?

**📝 Step 3 – Manual entry → Ticket**
- What is the status of my Google Workspace support case #GW-48217?
- Why was my Google Ads account ID 482-115-7790 suspended yesterday?
- When will my refund for Google Play order GPA.3341-2209-7781 be processed?
- Why was I charged twice for Google One storage on 20 Oct?

## Change your content
1. Put your files (PDF / TXT / MD) in the `knowledge/` folder.
2. Run `python ingest.py`, or click **🔄 Re-index all files** on the Knowledge Base page.

## Other commands
- `python main.py` – same agent in the terminal
- `python tickets.py` – list tickets in the terminal
- `python tickets.py answer 3` – answer ticket #3 in the terminal

## Common errors
| Error | Fix |
|---|---|
| `No module named 'dotenv'` / `streamlit: command not found` | Activate the venv: `source venv/bin/activate`, then `python -m pip install -r requirements.txt` |
| `No matching distribution found for crewai` | Your Python is 3.14. Recreate the venv with Anaconda Python 3.11: `rm -rf venv` then `/opt/anaconda3/bin/python -m venv venv` |
| `source: no such file or directory: venv/bin/activate` | The venv is missing (folder was replaced). Recreate it as in Setup. |
| `numpy.dtype size changed, may indicate binary incompatibility` | You ran Anaconda's Streamlit. Use `python -m streamlit run app.py` |
| `OPENAI_API_KEY not found` / `CHROMA_OPENAI_API_KEY is not set` | Create `.env` from `.env.example` and add your key. |
| `Operation not permitted` | System Settings → Privacy & Security → Files and Folders → allow Terminal / VS Code to access Downloads, or move the project to `~/Projects`. |
| "Share this execution trace with CrewAI?" prompt | Add `CREWAI_TRACING_ENABLED=false` to `.env` |
| Port 8501 busy | `python -m streamlit run app.py --server.port 8502` and open http://localhost:8502 |

## Don't do this
- Don't unzip a new copy over your working folder; it deletes `venv`, `.env` and `data/`.
- Don't create the venv with `python3 -m venv venv` (that's Python 3.14 on this Mac).
