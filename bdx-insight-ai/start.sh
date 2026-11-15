#!/usr/bin/env bash
# Starts the API (FastAPI on 127.0.0.1:8000) and the dashboard (Streamlit on :8501) together.
# Used by Docker; you can also run it directly on your Mac:  bash start.sh
set -e
cd "$(dirname "$0")"
uvicorn app.api:app --host 127.0.0.1 --port 8000 &
API_PID=$!
for _ in $(seq 1 30); do curl -sf http://127.0.0.1:8000/health >/dev/null && break; sleep 1; done
streamlit run ui/app.py --server.address=0.0.0.0 --server.port=8501 &
UI_PID=$!
trap 'kill $API_PID $UI_PID 2>/dev/null' INT TERM
wait -n $API_PID $UI_PID   # if either stops, stop the container so Docker restarts it
exit 1
