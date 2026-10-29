# 🛰️ SK Support Hub — Multi-Agent Customer Support Chatbot

A customer-support chatbot built with **Microsoft AutoGen** (multi-agent framework), **OpenAI**, and a **Streamlit** dashboard.
One **Head Agent (parent)** reads every question and assigns work to **department agents (children)** — IT, HR, Finance, Sales and Marketing. Each child uses its own tools, pushes its result back to the parent, and the parent sends one combined reply.

---

## 1. Architecture — how many agents?

**6 agents in total: 1 parent + 5 children.**

```
                    ┌────────────────────────────┐
   Customer ───────▶│  Head_Agent  (PARENT)      │  understands the request,
                    │  router / supervisor        │  picks the department(s)
                    └──┬──────┬──────┬──────┬────┬┘
          assigns task │      │      │      │    │
                    ┌──▼─┐ ┌──▼─┐ ┌──▼──┐ ┌─▼──┐ ┌▼────┐
                    │ IT │ │ HR │ │ FIN │ │SALES│ │ MKT │   CHILD agents
                    └─┬──┘ └─┬──┘ └──┬──┘ └─┬──┘ └┬────┘   (each has its own tools)
                      └──────┴───────┴──────┴─────┘
                          results pushed back
                                  │
                    Head_Agent merges ──▶ one final answer
```

| # | Agent | Role | Tools it can call |
|---|-------|------|-------------------|
| 1 | **Head_Agent** | Parent. Routes, delegates, merges answers | `delegate_to_it`, `delegate_to_hr`, `delegate_to_finance`, `delegate_to_sales`, `delegate_to_marketing` |
| 2 | **IT_Agent** | VPN, passwords, outages, tickets | `check_system_status`, `create_it_ticket`, `password_reset_steps` |
| 3 | **HR_Agent** | Leave, benefits, payroll dates | `get_leave_policy`, `check_leave_balance`, `get_benefits_info` |
| 4 | **Finance_Agent** | Invoices, refunds, reimbursements | `get_invoice_status`, `get_reimbursement_policy`, `raise_refund_request` |
| 5 | **Sales_Agent** | Pricing, orders, demos | `get_pricing`, `check_order_status`, `book_demo` |
| 6 | **Marketing_Agent** | Campaigns, webinars/events, brand assets | `get_campaign_info`, `get_upcoming_events`, `get_brand_assets` |

If a question touches two departments (e.g. *"My VPN is slow and how many leaves do I have?"*), the Head Agent assigns **both** children at the same time and merges both answers.

> You only need 4 departments for the assignment? Switch any agent off from the sidebar toggles — no code change needed.

### Dashboard features
- 💬 **Chat** — live panel shows the parent assigning tasks, each child calling tools, and results coming back
- 🕸️ **Agent Network** — graph of Customer → Head Agent → children → tools; the last run is highlighted
- 📊 **Analytics** — requests per department, tokens per agent, response time per question
- 🎫 **Tickets** — every ticket / refund / demo request the agents created (downloadable CSV)
- 🧾 **Run Trace** — step-by-step timeline of any past question
- Sidebar: model picker, turn departments on/off, clear chat

---

## 2. Project structure

```
autogen-support-hub/
├── app.py                  # Streamlit dashboard (front end)
├── cli_test.py             # Quick terminal test, no UI
├── agents/
│   ├── __init__.py
│   ├── config.py           # .env loading, OpenAI client, department definitions
│   ├── tools.py            # Each department's tools + sample data
│   └── orchestrator.py     # Parent-child AutoGen engine + tracing
├── .streamlit/config.toml  # Dark theme
├── requirements.txt        # Python packages
├── .env.example            # Template for your API key (safe to upload)
├── .gitignore              # Keeps .env out of GitHub
└── README.md
```

---

## 3. Step-by-step setup (first time with Python)

### Step 1 — Install the tools (one time)
1. **Python 3.10 or newer** → https://www.python.org/downloads/
   - On Windows, tick **"Add python.exe to PATH"** on the first installer screen.
2. **VS Code** (editor) → https://code.visualstudio.com/ — then install the **Python** extension inside VS Code.
3. **Git** → https://git-scm.com/downloads

Check in a terminal:
```bash
python --version      # should show 3.10+   (macOS/Linux: python3 --version)
git --version
```

### Step 2 — Open the project
1. Unzip `autogen-support-hub.zip` to a folder, e.g. `Documents/autogen-support-hub`.
2. VS Code → **File → Open Folder** → choose that folder.
3. Open a terminal: **Terminal → New Terminal**.

### Step 3 — Create a virtual environment (an isolated Python for this project)
**Windows (PowerShell):**
```powershell
python -m venv .venv
.venv\Scripts\activate
```
If you see *"running scripts is disabled"*, run this once, then activate again:
```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```
**macOS / Linux:**
```bash
python3 -m venv .venv
source .venv/bin/activate
```
You'll see `(.venv)` at the start of the terminal line — that means it's active.

### Step 4 — Install the packages
```bash
pip install -r requirements.txt
```

### Step 5 — Add your OpenAI API key with a `.env` file
1. Create a key at https://platform.openai.com/api-keys (your account needs billing credit).
2. Copy the template:
   - Windows: `copy .env.example .env`
   - macOS/Linux: `cp .env.example .env`
3. Open `.env` and paste your key:
   ```
   OPENAI_API_KEY=sk-proj-xxxxxxxxxxxxxxxx
   OPENAI_MODEL=gpt-4o-mini
   ```
4. Save. `.env` is listed in `.gitignore`, so it will **never** be uploaded to GitHub.

### Step 6 — Test the agents in the terminal
```bash
python cli_test.py
```
You should see the trace — Head_Agent assigning IT_Agent and HR_Agent, each child calling tools, results coming back — then the final answer.

### Step 7 — Launch the dashboard
```bash
streamlit run app.py
```
Your browser opens **http://localhost:8501**. Click a sample question or type your own.
Stop the app with **Ctrl + C** in the terminal.

---

## 4. Upload to GitHub (step by step)

1. Go to https://github.com/new → name it `autogen-support-hub` → **Public** or **Private** → **do not** tick "Add a README" → **Create repository**.
2. In the VS Code terminal (inside the project folder):
   ```bash
   git init
   git add .
   git status
   ```
   ✅ Check that `.env` is **NOT** in the list. You should see `.env.example` only.
3. Commit and push (replace `YOUR-USERNAME`):
   ```bash
   git commit -m "Multi-agent customer support chatbot with AutoGen + Streamlit"
   git branch -M main
   git remote add origin https://github.com/YOUR-USERNAME/autogen-support-hub.git
   git push -u origin main
   ```
4. First push asks you to sign in to GitHub — a browser window opens; approve it.
5. Later changes:
   ```bash
   git add .
   git commit -m "describe the change"
   git push
   ```

> ⚠️ If you ever push your key by mistake, **delete that key** on platform.openai.com immediately and create a new one. Removing the file from GitHub is not enough.

---

## 5. How the parent-child code works

All of it lives in `agents/orchestrator.py`:

1. **Children** — each department is an AutoGen `AssistantAgent` with its own tools (`_make_child`).
2. **Delegation tools** — for every child the parent receives a tool called `delegate_to_<department>(task)` (`_make_delegate_tool`). When the parent calls it:
   - the child agent is started with that task → **task assigned**
   - the child calls its own tools (e.g. `check_leave_balance`)
   - the child's answer is returned as the tool result → **data pushed back to the parent**
3. **Parent** — the Head Agent (`_make_head`) has only delegation tools, so it must route instead of guessing. With `reflect_on_tool_use=True` it writes one final reply after the children report back.
4. **Tracing** — every step fires a `TraceEvent`, which the dashboard draws live.

---

## 6. Customize

**Add a new department (e.g. Legal):**
1. `agents/config.py` → add an entry to `DEPARTMENTS` (`name`, `label`, `icon`, `color`, `scope`, `persona`).
2. `agents/tools.py` → write 2–3 functions and add them to `registry` under the same key.
3. Restart the app. The parent automatically gets `delegate_to_legal`, and the dashboard shows the new agent.

**Connect real systems:** `tools.py` uses sample data. Replace a function's body with an API call — e.g. `create_it_ticket` → ServiceNow/Jira, `check_leave_balance` → Workday/Darwinbox, `get_upcoming_events` → ON24/Cvent, `get_campaign_info` → Marketo/Eloqua. Keep the function name, type hints and docstring; the agents use them to decide when to call the tool.

**Try these sample IDs:** employees `EMP1001–EMP1003`, invoices `INV-2041–INV-2043`, orders `ORD-7781–ORD-7783`.

---

## 7. Troubleshooting

| Problem | Fix |
|---|---|
| `python` not recognized | Reinstall Python with **Add to PATH** ticked, or use `py` on Windows |
| `No module named autogen_agentchat` | Activate the venv (Step 3), then `pip install -r requirements.txt` |
| Red "No OPENAI_API_KEY found" in sidebar | `.env` must be in the project root (next to `app.py`), named exactly `.env` |
| `401 Incorrect API key` | Key copied wrongly or revoked — create a new one |
| `429 insufficient_quota` | Add billing credit on platform.openai.com |
| Port 8501 busy | `streamlit run app.py --server.port 8502` |

---

**Tech stack:** Python · Microsoft AutoGen AgentChat 0.7 · OpenAI · Streamlit · Plotly
