#!/usr/bin/env bash
# One command to install everything and start Beldex on a Mac:   bash run_mac.sh
set -e
cd "$(dirname "$0")"

# 1. Pick a Python: 3.12 or 3.13 if available (full CrewAI), otherwise python3
PY=""
for p in python3.12 python3.13 python3; do
  if command -v "$p" >/dev/null 2>&1; then PY="$p"; break; fi
done
echo "==> Using $($PY --version)"

# 2. Virtual environment (re-used if it already exists)
if [ ! -x .venv/bin/python ]; then
  echo "==> Creating virtual environment .venv"
  "$PY" -m venv .venv
fi
source .venv/bin/activate

# 3. Packages + the browser for the crawler
echo "==> Installing packages (first time: 3-6 minutes)"
python -m pip install --upgrade pip -q
python -m pip install -r requirements.txt -q
echo "==> Installing Chromium for Playwright"
python -m playwright install chromium

# 4. Settings check
[ -f .env ] || cp .env.example .env
grep -q "^OPENAI_API_KEY=sk-" .env || echo "    NOTE: OPENAI_API_KEY is empty in .env -> answers show matching passages only. Paste your key there for full AI answers."

# 5. Start API + dashboard
echo
echo "==> Starting Beldex AI. Open http://localhost:8501   (stop with Ctrl+C)"
echo "    Admin login: see ADMIN_EMAIL / ADMIN_PASSWORD in .env"
bash start.sh
