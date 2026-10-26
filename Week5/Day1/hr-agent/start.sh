#!/usr/bin/env bash
# One-click start for macOS / Linux: sets up everything and opens the app.
set -e
cd "$(dirname "$0")"

PY=python3
command -v $PY >/dev/null 2>&1 || PY=python

if [ ! -d venv ]; then
  echo "Creating virtual environment..."
  $PY -m venv venv
fi

source venv/bin/activate

echo "Installing packages (first run can take a minute)..."
python -m pip install --upgrade pip -q
python -m pip install -r requirements.txt -q

if [ ! -f .env ]; then
  cp .env.example .env
  echo ""
  echo "A .env file was created. Open it, paste your OpenAI API key after"
  echo "OPENAI_API_KEY=, save, then run ./start.sh again."
  exit 0
fi

echo ""
echo "Starting the app at http://127.0.0.1:8000 ..."
python app.py
