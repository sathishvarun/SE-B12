#!/usr/bin/env bash
# Starts Beldex AI: API + web app on one port.  Open http://localhost:8501
set -e
cd "$(dirname "$0")"
PORT="${PORT:-8501}"
exec uvicorn app.api:app --host "${HOST:-0.0.0.0}" --port "$PORT"
