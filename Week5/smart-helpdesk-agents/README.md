# 🎧 SK Soft Technology Help Desk — Multi-Agent Support with AutoGen + Streamlit

An AI help desk for **SK Soft Technology**, an IT services company. A team of AI agents reads a query from an
**employee**, sends it to the right **department agent** (Client Support, Finance, Marketing, Sales, HR, IT), sets a
**priority** (High / Medium / Low), answers **only from company documents**, escalates hard
cases to a human, and saves **every ticket to TXT + CSV** with a **weekly view**.

Runs on your Mac at `http://localhost:8501` and deploys to any VPS.

---

## 1. How it works

```
 Query typed in Streamlit
          │
          ▼
 🧭 Router Agent (MAIN agent)  → department · category · priority · sentiment · summary
          │
          ▼  picks ONE department sub-agent
 🛟 Client Support │ 💳 Finance │ 📣 Marketing │ 💼 Sales │ 👥 HR │ 🖥️ IT
          │  calls search_kb() on its own folder (+ optional SerpAPI web_search)
          ▼
 ✍️ Resolution Agent  → polite reply using ONLY the facts found + CONFIDENCE
          │
          ▼
 🗂️ Log Agent  → calls log_ticket() → logs/tickets.csv + logs/tickets.txt
                 → Resolved ✅  or  Escalated 🚨 to "<Department> human team"
```

* Step 1 runs the Router alone (so we know which sub-agent to call).
* Step 2 is an AutoGen **RoundRobinGroupChat**: Department → Resolution → Log.
  It stops on `TextMentionTermination("LOGGED")` with `MaxMessageTermination(12)` as a safety net.

### Escalation rules (any one = Escalated)
| Rule | Example |
|---|---|
| Priority is **High** | system down, money charged wrongly |
| Sentiment is **Angry** | "Fix this NOW!" |
| No matching document | a question no company document covers |
| Legal / fraud / payment dispute / harassment words | lawyer, bank, chargeback, harass |
| Resolution confidence is **Low** | partial facts |
| Log Agent decides a human is needed | its own judgement |

Anti-hallucination: the Log Agent can only record source files that `search_kb` really returned.

### Log columns
`ticket_id, timestamp, employee_name, employee_id, department, category, priority, sentiment,
summary, complaint, kb_sources, response, confidence, status, escalation_reason, assigned_to`
(priority = urgency).

---

## 2. Step-by-step setup on your Mac

### Step 0 — One-time tools
Open **Terminal** (Cmd + Space → "Terminal") and check Python:
```bash
python3 --version        # needs 3.10 or newer
```
If it's missing or older, install Homebrew and Python:
```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
brew install python@3.11 git
```
Recommended editor: VS Code (https://code.visualstudio.com).

### Step 1 — Put the project in a folder
Unzip `smart-helpdesk-agents.zip` into, for example, `~/Projects/`, then:
```bash
cd ~/Projects/smart-helpdesk-agents
```

### Step 2 — Create and activate a virtual environment
```bash
python3 -m venv .venv
source .venv/bin/activate          # your prompt now starts with (.venv)
```
Every time you open a new Terminal, run `cd` into the folder and `source .venv/bin/activate` again.

### Step 3 — Install the packages
```bash
pip install --upgrade pip
pip install -r requirements.txt
```
This installs: `autogen-agentchat`, `autogen-ext[openai]`, `streamlit`, `python-dotenv`,
`pandas`, `openpyxl`, `requests`.

### Step 4 — Add your API keys
```bash
cp .env.example .env
open -e .env                       # opens in TextEdit
```
* `OPENAI_API_KEY` — **required**. Get it at https://platform.openai.com/api-keys
* `SERPAPI_API_KEY` — optional. Get it at https://serpapi.com/manage-api-key
  (when set, department agents can also search the public web for non-policy facts).
* `APP_PASSWORD` — optional locally, **recommended on the VPS**.
* `SHOW_AGENT_STEPS` — `false` (default): employees see **only the answer** — no file names, no agent steps.
  Set it to `true` for demos and assignment screenshots: each answer then shows its source file and a
  **Behind the scenes** panel with every agent's step, and the sidebar shows the AI model status.

### Step 5 — Quick test in the terminal
```bash
python team.py
```
You should see each agent speak and end with `FINAL: Resolved | ...`.

### Step 6 — Run the app on localhost
```bash
streamlit run app.py
```
Open **http://localhost:8501**. Stop it with `Ctrl + C`.

### Step 7 — Try it
1. **💬 Ask** → enter your name and Employee ID, then type a question in the box at the bottom, or pick
   a team in the one-line example bar and tap one of its questions (Client Support, Finance, Marketing, Sales, HR, IT).
2. A live progress line shows the request being routed, searched and answered. The answer shows a
   **✅ Solved** or **🙋 Passed to a person** badge, the team, priority and ticket number.
   Open **🔍 Behind the scenes** to see every agent's step.
3. **🗂️ Ticket history** → search and filter, click a row for the full ticket, download **Excel, CSV or TXT**.
4. **📊 Weekly summary** → pick any day → totals, questions per team, solved vs passed to a person,
   tickets per day, tickets waiting for a person, and a **weekly TXT report** download.
5. **Name and Employee ID are mandatory**: the app asks for them first, saves them on every ticket,
   and shows them in the sidebar (use **Change details** to switch user).

---

## 3. Project structure
```
smart-helpdesk-agents/
├── app.py                     # Streamlit UI (ticket form, timeline, log, weekly view)
├── team.py                    # wires Router → Department → Resolution → Log
├── config.py                  # keys, paths, department list, model client
├── agents/
│   ├── router_agent.py        # MAIN agent: department + priority + sentiment
│   ├── department_agents.py   # sub-agents: Support, Finance, Marketing, Sales, HR, IT
│   ├── resolution_agent.py    # grounded reply + confidence
│   └── log_agent.py           # log_ticket tool + escalation decision
├── tools/
│   ├── kb_search.py           # keyword search over knowledge_base/
│   ├── web_search.py          # optional SerpAPI search
│   └── ticket_store.py        # CSV/TXT logging + escalation rules
├── knowledge_base/
│   ├── customer_support/      # Client Support: SLA/P1 incidents, tickets, portal, releases
│   ├── finance/  marketing/  sales/  hr/  it/
├── logs/                      # tickets.csv + tickets.txt (created automatically)
├── deploy/                    # nginx.conf + systemd service for the VPS
├── Dockerfile, docker-compose.yml
├── screenshots/               # add your screenshots here for submission
├── .env.example, .gitignore, requirements.txt
```

### Add or change a department
1. Create a folder in `knowledge_base/`, e.g. `knowledge_base/legal/`, and add `.md` files.
2. Add one line in `config.py` → `DEPARTMENTS` and `DEPARTMENT_LABELS`.
That's it — the Router and the new sub-agent pick it up automatically.

---

## 4. Push to GitHub
```bash
git init
git add .
git status                 # make sure .env is NOT listed
git commit -m "Smart help desk multi-agent app"
git branch -M main
git remote add origin https://github.com/<your-username>/smart-helpdesk-agents.git
git push -u origin main
```

---

## 5. Host it on your VPS (Ubuntu 22.04 / 24.04)

> **Easiest way:** follow **DEPLOY_VPS.md** — copy the folder with one `rsync` command, then run
> `bash deploy/setup_vps.sh` on the VPS. It does all the steps below for you.

### 5.1 Connect and prepare
```bash
ssh ubuntu@YOUR_VPS_IP
sudo apt update && sudo apt install -y git nginx
git clone https://github.com/<your-username>/smart-helpdesk-agents.git
cd smart-helpdesk-agents
cp .env.example .env && nano .env      # paste keys, set APP_PASSWORD, save with Ctrl+O, Enter, Ctrl+X
```

### 5.2 Option A — Docker (easiest)
```bash
curl -fsSL https://get.docker.com | sudo sh
sudo docker compose up -d --build
sudo docker compose logs -f          # Ctrl+C to leave the logs
```

### 5.2 Option B — Without Docker (systemd)
```bash
sudo apt install -y python3-venv
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
sudo cp deploy/smart-helpdesk.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now smart-helpdesk
sudo systemctl status smart-helpdesk
```

### 5.3 Put Nginx in front (both options)
```bash
sudo cp deploy/nginx.conf /etc/nginx/sites-available/helpdesk
sudo nano /etc/nginx/sites-available/helpdesk     # replace YOUR_DOMAIN_OR_IP
sudo ln -s /etc/nginx/sites-available/helpdesk /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t && sudo systemctl reload nginx
sudo ufw allow OpenSSH && sudo ufw allow 'Nginx Full' && sudo ufw enable
```
Open `http://YOUR_DOMAIN_OR_IP`.

### 5.4 Free HTTPS (if you have a domain)
```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d yourdomain.com
```

### 5.5 Update after code changes
```bash
cd ~/smart-helpdesk-agents && git pull
sudo docker compose up -d --build        # Option A
sudo systemctl restart smart-helpdesk    # Option B
```

---

## 6. Troubleshooting
| Problem | Fix |
|---|---|
| `command not found: streamlit` | Activate the venv: `source .venv/bin/activate` |
| `OPENAI_API_KEY is missing` | Check `.env` is in the project folder and restart the app |
| `401 Unauthorized` / `insufficient_quota` | Wrong key or no OpenAI credits |
| Port 8501 busy | `streamlit run app.py --server.port 8502` |
| Answer says "no information" | Add the fact to a `.md` file in the right `knowledge_base/` folder |
| VPS page keeps loading | Nginx needs the websocket lines from `deploy/nginx.conf` |

**Never** share your API key in screenshots or commits. If a key leaks, revoke it and make a new one.

---

## 7. Assignment checklist mapping
| Requirement | Where |
|---|---|
| Four AutoGen agents with clear jobs (Query, Knowledge, Resolution, Log) | Router = Query Agent, Department agents = Knowledge Agent, plus Resolution and Log |
| `search_kb(query)` with file names | `agents/department_agents.py`, `tools/kb_search.py` |
| No invented policies | Resolution system message + verified sources in `log_ticket` |
| Order + termination | `team.py` (RoundRobinGroupChat, `LOGGED` + max messages) |
| Escalation rule | `tools/ticket_store.py → escalation_check` |
| Log file with all columns | `logs/tickets.csv`, `logs/tickets.txt`, Excel download |
| Streamlit UI with steps, badges, log viewer | `app.py` |
| Bonus: dashboard, same-language reply, Docker deploy | Weekly view, Resolution prompt, Dockerfile |
